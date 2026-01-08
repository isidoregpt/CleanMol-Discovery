import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .context_slice import slice_pages
from .repair_opus import repair_entity_with_opus
from .db import insert_repair, update_molecule, update_experiment, update_result, insert_evidence

def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def _index(extraction: dict) -> dict:
    return {
        "molecule": {m.get("molecule_id"): m for m in (extraction.get("molecules") or [])},
        "experiment": {e.get("experiment_id"): e for e in (extraction.get("experiments") or [])},
        "result": {r.get("result_id"): r for r in (extraction.get("results") or [])},
    }

def auto_repair(*, conn, doc_id: str, bundle_dir: Path, paper_md: str, extraction: dict,
                audit_json: dict, anthropic_key: str, opus_model: str, max_repairs: int = 25) -> dict:
    idx = _index(extraction)
    applied = []
    attempted = 0

    for a in (audit_json.get("audits") or []):
        if a.get("verdict") == "SUPPORTED":
            continue
        if attempted >= max_repairs:
            break

        et = a["entity_type"]
        eid = a["entity_id"]
        issues = a.get("issues") or []
        suggested_fix = a.get("suggested_fix")

        original = idx.get(et, {}).get(eid)
        if not original:
            continue

        before = json.dumps(original, ensure_ascii=False)

        candidate = None
        if isinstance(suggested_fix, dict) and suggested_fix:
            candidate = dict(original)
            candidate.update(suggested_fix)

        if candidate is None:
            page = ((original.get("evidence") or {}).get("page")) or 1
            try:
                page = int(page)
            except Exception:
                page = 1
            page_slice_md = slice_pages(paper_md, [page], pad=1)
            repair_out = repair_entity_with_opus(
                anthropic_key=anthropic_key, model=opus_model,
                entity_type=et, entity=original,
                verdict=a.get("verdict","AMBIGUOUS"),
                issues=issues,
                page_slice_md=page_slice_md
            )
            candidate = repair_out.get("repaired_entity") or original

        after = json.dumps(candidate, ensure_ascii=False)
        did_apply = False

        try:
            ev = candidate.get("evidence")
            if ev:
                insert_evidence(conn, doc_id, ev)

            if et == "molecule":
                candidate["molecule_id"] = original["molecule_id"]
                update_molecule(conn, candidate)
            elif et == "experiment":
                candidate["experiment_id"] = original["experiment_id"]
                update_experiment(conn, doc_id, candidate)
            elif et == "result":
                candidate["result_id"] = original["result_id"]
                update_result(conn, doc_id, candidate)

            idx[et][eid] = candidate
            did_apply = True
            applied.append({"entity_type": et, "entity_id": eid, "verdict": a.get("verdict")})
        except Exception:
            did_apply = False

        insert_repair(conn, {
            "repair_id": str(uuid.uuid4()),
            "doc_id": doc_id,
            "entity_type": et,
            "entity_id": eid,
            "model": opus_model,
            "reason": f"audit:{a.get('verdict')}",
            "before_json": before,
            "after_json": after,
            "applied": 1 if did_apply else 0,
            "created_at": _utc_iso(),
        })

        attempted += 1

    repaired = dict(extraction)
    repaired["molecules"] = list(idx["molecule"].values())
    repaired["experiments"] = list(idx["experiment"].values())
    repaired["results"] = list(idx["result"].values())

    (bundle_dir / "extraction_repaired.json").write_text(
        json.dumps(repaired, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {"repairs_attempted": attempted, "repairs_applied": applied, "extraction": repaired}
