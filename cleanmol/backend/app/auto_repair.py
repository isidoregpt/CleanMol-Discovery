import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from .context_slice import slice_pages
from .repair_opus import repair_entity_with_opus
from .db import insert_repair, update_molecule, update_experiment, update_result, insert_evidence
from .logger import PipelineLogger


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _index(extraction: dict) -> dict:
    return {
        "molecule": {m.get("molecule_id"): m for m in (extraction.get("molecules") or [])},
        "experiment": {e.get("experiment_id"): e for e in (extraction.get("experiments") or [])},
        "result": {r.get("result_id"): r for r in (extraction.get("results") or [])},
    }


def auto_repair(*, conn, doc_id: str, bundle_dir: Path, paper_md: str, extraction: dict,
                audit_json: dict, anthropic_key: str, opus_model: str, max_repairs: int = 25,
                logger: Optional[PipelineLogger] = None) -> dict:
    """
    Auto-repair entities that failed audit.

    Returns:
        dict with repair report and updated extraction
    """
    start_time = time.time()

    # Backup existing SMILES before repair
    existing_smiles = {}
    for mol in (extraction.get("molecules") or []):
        mol_id = mol.get("molecule_id")
        if mol_id and mol.get("smiles"):
            existing_smiles[mol_id] = {
                "smiles": mol.get("smiles"),
                "smiles_source": mol.get("smiles_source"),
                "smiles_valid": mol.get("smiles_valid"),
                "smiles_confidence": mol.get("smiles_confidence")
            }

    if existing_smiles:
        print(f"  [DEBUG auto_repair] Backing up SMILES for {len(existing_smiles)} molecules")

    idx = _index(extraction)
    applied = []
    failed = []
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
                verdict=a.get("verdict", "AMBIGUOUS"),
                issues=issues,
                page_slice_md=page_slice_md,
                logger=logger
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
        except Exception as e:
            did_apply = False
            failed.append({"entity_type": et, "entity_id": eid, "error": str(e)})

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

    # Restore SMILES that may have been lost during repair
    restored_count = 0
    for mol in (repaired.get("molecules") or []):
        mol_id = mol.get("molecule_id")
        if mol_id in existing_smiles and not mol.get("smiles"):
            smiles_data = existing_smiles[mol_id]
            mol["smiles"] = smiles_data["smiles"]
            mol["smiles_source"] = smiles_data.get("smiles_source")
            mol["smiles_valid"] = smiles_data.get("smiles_valid")
            mol["smiles_confidence"] = smiles_data.get("smiles_confidence")
            restored_count += 1

    if restored_count > 0:
        print(f"  [DEBUG auto_repair] Restored SMILES for {restored_count} molecules")

    final_smiles_count = sum(1 for m in repaired.get("molecules", []) if m.get("smiles"))
    print(f"  [DEBUG auto_repair] After repair: {final_smiles_count} molecules have SMILES")

    elapsed = time.time() - start_time

    (bundle_dir / "extraction_repaired.json").write_text(
        json.dumps(repaired, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return {
        "repairs_attempted": attempted,
        "repairs_applied": applied,
        "repairs_failed": failed,
        "extraction": repaired,
        "_meta": {
            "time": elapsed,
            "attempted": attempted,
            "applied": len(applied),
            "failed": len(failed)
        }
    }
