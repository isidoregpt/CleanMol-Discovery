import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

from .db import (
    connect_db, init_db, insert_run, insert_document,
    insert_molecule, insert_experiment, insert_result, insert_evidence,
    insert_audit, insert_gap
)
from .pdf_bundle import extract_bundle
from .extract_opus import run_opus_extraction
from .audit_and_gap import run_auditor, run_gap_hunter
from .auto_repair import auto_repair
from .gap_resolve import resolve_gaps_with_targeted_opus
from .export_jsonl import export_jsonl

def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _write_bundle_file(bundle_dir: Path, name: str, obj: dict):
    (bundle_dir / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def _upsert_extraction_into_db(conn, doc_id: str, extraction: dict):
    for mol in extraction.get("molecules", []) or []:
        if mol.get("evidence"):
            insert_evidence(conn, doc_id, mol["evidence"])
        insert_molecule(conn, doc_id, mol)

    for exp in extraction.get("experiments", []) or []:
        if exp.get("evidence"):
            insert_evidence(conn, doc_id, exp["evidence"])
        insert_experiment(conn, doc_id, exp)

    for res in extraction.get("results", []) or []:
        if res.get("evidence"):
            insert_evidence(conn, doc_id, res["evidence"])
        if not res.get("experiment_id"):
            res["experiment_id"] = "unknown"
        insert_result(conn, doc_id, res)

def run_pipeline(*, input_dir: str, output_dir: str, models: dict, keys: dict, options: dict) -> dict:
    input_path = Path(input_dir)
    out = Path(output_dir)
    bundles_root = out / "bundles"
    bundles_root.mkdir(parents=True, exist_ok=True)
    (out / "logs").mkdir(exist_ok=True)
    (out / "versions").mkdir(exist_ok=True)

    db_path = out / "dataset.db"
    conn = connect_db(db_path)
    init_db(conn)

    run_id = str(uuid.uuid4())
    started = _utc_iso()

    primary_model = models.get("primary","")
    auditor_model = models.get("auditor","")
    gap_model = models.get("gapHunter","")

    anthropic_key = keys.get("anthropic","")
    openai_key = keys.get("openai","")
    gemini_key = keys.get("gemini","")

    max_gap_rounds = int(options.get("max_gap_rounds", 2))
    errors = []
    processed = []

    pdfs = sorted([p for p in input_path.glob("*.pdf") if p.is_file()])

    for pdf in pdfs:
        try:
            bundle = extract_bundle(pdf, bundles_root)
            doc_id = bundle["doc_id"]
            bundle_dir = Path(bundle["bundle_path"])
            meta = bundle["metadata"]

            insert_document(conn, {
                "doc_id": doc_id,
                "source_type": "paper",
                "title": None, "doi": None, "year": None,
                "path": meta["path"],
                "bundle_path": str(bundle_dir),
                "created_at": meta["created_at"]
            })

            paper_md_path = bundle_dir / "paper.md"
            paper_md = paper_md_path.read_text(encoding="utf-8")

            # 1) Opus extraction
            if not (anthropic_key and primary_model):
                raise ValueError("Missing Anthropic key or primary model.")
            extraction = run_opus_extraction(
                anthropic_key=anthropic_key,
                model=primary_model,
                bundle_dir=bundle_dir,
                paper_md_path=paper_md_path
            )
            _write_bundle_file(bundle_dir, "extraction_current.json", extraction)
            _upsert_extraction_into_db(conn, doc_id, extraction)

            # 2) Audit
            if openai_key and auditor_model:
                audit_json = run_auditor(
                    openai_key=openai_key, model=auditor_model,
                    paper_md=paper_md, extraction=extraction
                )
                _write_bundle_file(bundle_dir, "audit_gpt52.json", audit_json)

                for a in audit_json.get("audits", []) or []:
                    insert_audit(conn, {
                        "audit_id": str(uuid.uuid4()),
                        "doc_id": doc_id,
                        "entity_type": a["entity_type"],
                        "entity_id": a["entity_id"],
                        "model": auditor_model,
                        "verdict": a["verdict"],
                        "confidence": float(a.get("confidence", 0.0)),
                        "issues_json": json.dumps(a.get("issues", [])),
                        "suggested_fix_json": json.dumps(a.get("suggested_fix")) if a.get("suggested_fix") else None,
                        "created_at": _utc_iso(),
                    })

                # 3) Auto-repair (Opus)
                repair_report = auto_repair(
                    conn=conn, doc_id=doc_id, bundle_dir=bundle_dir,
                    paper_md=paper_md, extraction=extraction, audit_json=audit_json,
                    anthropic_key=anthropic_key, opus_model=primary_model,
                    max_repairs=25
                )
                _write_bundle_file(bundle_dir, "repair_report.json", repair_report)
                extraction = repair_report["extraction"]

            # 4) Gap hunt
            gaps_json = None
            if gemini_key and gap_model:
                gaps_json = run_gap_hunter(
                    gemini_key=gemini_key, model=gap_model,
                    paper_md=paper_md, extraction=extraction
                )
                _write_bundle_file(bundle_dir, "gaps_gemini.json", gaps_json)
                for g in gaps_json.get("gaps", []) or []:
                    insert_gap(conn, {
                        "suggestion_id": str(uuid.uuid4()),
                        "doc_id": doc_id,
                        "model": gap_model,
                        "kind": g["kind"],
                        "page": g.get("page"),
                        "description": g["description"],
                        "rationale": g.get("rationale"),
                        "created_at": _utc_iso(),
                    })

            # 5) Gap resolution loop (targeted Opus)
            if gaps_json is not None:
                for round_i in range(max_gap_rounds):
                    resolve_out = resolve_gaps_with_targeted_opus(
                        anthropic_key=anthropic_key,
                        opus_model=primary_model,
                        paper_md=paper_md,
                        extraction=extraction,
                        gaps_json=gaps_json,
                        bundle_dir=bundle_dir,
                        max_targets=10
                    )
                    extraction = resolve_out["extraction"]
                    _write_bundle_file(bundle_dir, f"extraction_after_gap_round_{round_i+1}.json", extraction)
                    _upsert_extraction_into_db(conn, doc_id, extraction)

                    # Re-audit after gap additions
                    if openai_key and auditor_model:
                        audit2 = run_auditor(
                            openai_key=openai_key, model=auditor_model,
                            paper_md=paper_md, extraction=extraction
                        )
                        _write_bundle_file(bundle_dir, f"audit_after_gap_round_{round_i+1}.json", audit2)
                        repair2 = auto_repair(
                            conn=conn, doc_id=doc_id, bundle_dir=bundle_dir,
                            paper_md=paper_md, extraction=extraction, audit_json=audit2,
                            anthropic_key=anthropic_key, opus_model=primary_model,
                            max_repairs=25
                        )
                        _write_bundle_file(bundle_dir, f"repair_after_gap_round_{round_i+1}.json", repair2)
                        extraction = repair2["extraction"]

                    # Re-run gap hunter
                    if gemini_key and gap_model:
                        gaps_json = run_gap_hunter(
                            gemini_key=gemini_key, model=gap_model,
                            paper_md=paper_md, extraction=extraction
                        )
                        _write_bundle_file(bundle_dir, f"gaps_after_round_{round_i+1}.json", gaps_json)

            # 6) Final export JSONL
            export_jsonl(out, doc_id, extraction)

            processed.append(doc_id)

        except Exception as e:
            errors.append({"pdf": str(pdf), "error": str(e)})

    status = "ok" if not errors else "failed"
    run_row = {
        "run_id": run_id,
        "started_at": started,
        "finished_at": _utc_iso(),
        "input_dir": str(input_path),
        "output_dir": str(out),
        "primary_model": primary_model,
        "auditor_model": auditor_model,
        "gap_model": gap_model,
        "status": status,
        "notes": f"Processed {len(processed)} PDFs; errors={len(errors)}; gap_rounds={options.get('max_gap_rounds',2)}",
    }
    insert_run(conn, run_row)
    conn.close()

    return {"run": run_row, "documents_processed": processed, "errors": errors}
