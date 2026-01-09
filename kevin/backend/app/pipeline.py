import json
import time
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
from .smiles_lookup import enrich_molecules_with_smiles
from .figure_analysis import analyze_pdf_figures, match_figure_compounds_to_molecules
from .smiles_validation import validate_and_enrich_smiles
from .excel_export import create_review_workbook, export_combined_workbook
from .logger import PipelineLogger


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_bundle_file(bundle_dir: Path, name: str, obj: dict):
    (bundle_dir / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _sanitize_foreign_keys(extraction: dict, logger=None) -> dict:
    """
    Ensure all results have valid experiment_id and molecule_id references.
    Invalid references are set to None and annotated with orphan metadata.
    This prevents FK constraint failures without inventing fake parent records.
    """
    existing_exp_ids = {e.get("experiment_id") for e in (extraction.get("experiments") or []) if e.get("experiment_id")}
    existing_mol_ids = {m.get("molecule_id") for m in (extraction.get("molecules") or []) if m.get("molecule_id")}

    orphan_count = 0
    for result in (extraction.get("results") or []):
        if "_meta" not in result:
            result["_meta"] = {}

        exp_id = result.get("experiment_id")
        mol_id = result.get("molecule_id")

        if exp_id and exp_id not in existing_exp_ids:
            result["_meta"]["orphan_experiment"] = True
            result["_meta"]["original_experiment_id"] = exp_id
            result["experiment_id"] = None
            orphan_count += 1

        if mol_id and mol_id not in existing_mol_ids:
            result["_meta"]["orphan_molecule"] = True
            result["_meta"]["original_molecule_id"] = mol_id
            result["molecule_id"] = None
            orphan_count += 1

    if orphan_count > 0 and logger:
        logger.log_warning(
            f"Nulled {orphan_count} orphan foreign key reference(s) in results",
            stage="FK Sanitization"
        )

    return extraction


def _upsert_extraction_into_db(conn, doc_id: str, extraction: dict):
    """
    Insert extraction data into database.
    Assumes extraction has been sanitized via _sanitize_foreign_keys first.
    Results with null experiment_id are skipped (orphan results).
    """
    # Insert molecules first
    for mol in extraction.get("molecules", []) or []:
        if mol.get("evidence"):
            insert_evidence(conn, doc_id, mol["evidence"])
        insert_molecule(conn, doc_id, mol)

    # Insert experiments second
    for exp in extraction.get("experiments", []) or []:
        if exp.get("evidence"):
            insert_evidence(conn, doc_id, exp["evidence"])
        insert_experiment(conn, doc_id, exp)

    # Insert results last - skip orphan results (null experiment_id)
    for res in extraction.get("results", []) or []:
        if res.get("evidence"):
            insert_evidence(conn, doc_id, res["evidence"])

        # Skip results without valid experiment_id (orphan results are nulled by sanitization)
        if not res.get("experiment_id"):
            continue

        insert_result(conn, doc_id, res)


def _get_db_stats(conn) -> dict:
    """Get counts from database tables."""
    stats = {}
    tables = ["molecules", "experiments", "results", "evidence", "audits", "repairs", "gap_suggestions"]
    for table in tables:
        try:
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            stats[table] = row[0] if row else 0
        except Exception:
            stats[table] = 0
    return stats


def run_pipeline(*, input_dir: str, output_dir: str, models: dict, keys: dict, options: dict, progress_callback=None) -> dict:
    input_path = Path(input_dir)
    out = Path(output_dir)
    bundles_root = out / "bundles"
    bundles_root.mkdir(parents=True, exist_ok=True)
    (out / "logs").mkdir(exist_ok=True)
    (out / "versions").mkdir(exist_ok=True)

    # Initialize logger
    config = {
        "input_dir": input_dir,
        "output_dir": output_dir,
        "models": models,
        "keys": keys,
        "options": options
    }
    logger = PipelineLogger(output_dir, config, progress_callback=progress_callback)

    db_path = out / "dataset.db"
    conn = connect_db(db_path)
    init_db(conn)

    run_id = str(uuid.uuid4())
    started = _utc_iso()

    primary_model = models.get("primary", "")
    auditor_model = models.get("auditor", "")
    gap_model = models.get("gapHunter", "")

    anthropic_key = keys.get("anthropic", "")
    openai_key = keys.get("openai", "")
    gemini_key = keys.get("gemini", "")

    max_gap_rounds = int(options.get("max_gap_rounds", 2))
    errors = []
    processed = []
    all_extractions = []  # Collect for combined Excel export

    pdfs = sorted([p for p in input_path.glob("*.pdf") if p.is_file()])
    doc_total = len(pdfs)

    for doc_i, pdf in enumerate(pdfs):
        doc_index = doc_i + 1
        doc_start_time = time.time()

        try:
            # Start document logging
            logger.start_document(pdf.name, "", str(pdf))

            # Stage 1: PDF Extraction
            logger.emit_progress("PDF", "start", doc_index=doc_index, doc_total=doc_total)
            stage_start = time.time()
            bundle = extract_bundle(pdf, bundles_root)
            doc_id = bundle["doc_id"]
            bundle_dir = Path(bundle["bundle_path"])
            meta = bundle["metadata"]
            stage_time = time.time() - stage_start

            # Update logger with doc_id and pages
            logger.current_doc["doc_id"] = doc_id
            logger.set_document_pages(meta.get("pages", 0))

            paper_md_path = bundle_dir / "paper.md"
            paper_md = paper_md_path.read_text(encoding="utf-8")

            logger.log_stage("Stage 1: PDF Extraction", {
                "status": "success",
                "time": stage_time,
                "pages_extracted": meta.get("pages", 0),
                "characters_extracted": len(paper_md),
                "bundle_path": str(bundle_dir)
            })
            logger.emit_progress("PDF", "end", doc_index=doc_index, doc_total=doc_total,
                                stats={"pages": meta.get("pages", 0), "chars": len(paper_md)})

            insert_document(conn, {
                "doc_id": doc_id,
                "source_type": "paper",
                "title": None, "doi": None, "year": None,
                "path": meta["path"],
                "bundle_path": str(bundle_dir),
                "created_at": meta["created_at"]
            })

            # Stage 2: Figure Analysis (extract chemical structures from figures)
            figure_compounds = []
            figure_analysis_enabled = options.get("figure_analysis", {}).get("enabled", True)
            if figure_analysis_enabled and anthropic_key:
                logger.emit_progress("FIGURE", "start", doc_index=doc_index, doc_total=doc_total)
                stage_start = time.time()

                try:
                    figure_config = options.get("figure_analysis", {})
                    figure_results = analyze_pdf_figures(
                        pdf_path=str(pdf),
                        api_key=anthropic_key,
                        figure_pages=figure_config.get("figure_pages"),
                        model=figure_config.get("model", primary_model),
                        min_image_size=figure_config.get("min_image_size", 200)
                    )

                    figure_compounds = figure_results.get("compounds", [])
                    figure_stats = figure_results.get("stats", {})
                    stage_time = time.time() - stage_start

                    _write_bundle_file(bundle_dir, "figure_analysis.json", figure_results)

                    logger.log_stage("Stage 2: Figure Analysis", {
                        "status": "success",
                        "time": stage_time,
                        "images_analyzed": figure_stats.get("images_analyzed", 0),
                        "structures_found": figure_stats.get("structures_found", 0),
                        "structures_valid": figure_stats.get("structures_valid", 0)
                    })
                    logger.emit_progress("FIGURE", "end", doc_index=doc_index, doc_total=doc_total,
                                        stats={"structures": figure_stats.get("structures_valid", 0)})
                except Exception as e:
                    stage_time = time.time() - stage_start
                    logger.log_warning(f"Figure analysis failed: {e}", stage="Figure Analysis")
                    logger.log_stage("Stage 2: Figure Analysis", {
                        "status": "error",
                        "time": stage_time,
                        "error": str(e)
                    })
                    logger.emit_progress("FIGURE", "end", doc_index=doc_index, doc_total=doc_total,
                                        stats={"structures": 0})
            else:
                logger.log_stage("Stage 2: Figure Analysis", {
                    "status": "skipped",
                    "reason": "Disabled or no Anthropic key"
                })

            # Stage 3: Opus Extraction
            logger.emit_progress("OPUS", "start", doc_index=doc_index, doc_total=doc_total)
            stage_start = time.time()
            if not (anthropic_key and primary_model):
                raise ValueError("Missing Anthropic key or primary model.")

            extraction = run_opus_extraction(
                anthropic_key=anthropic_key,
                model=primary_model,
                bundle_dir=bundle_dir,
                paper_md_path=paper_md_path,
                logger=logger
            )

            extraction_meta = extraction.pop("_meta", {})
            stage_time = time.time() - stage_start

            logger.log_stage("Stage 3: Opus Extraction", {
                "status": "success",
                "time": stage_time,
                "model": primary_model,
                "tokens_in": extraction_meta.get("tokens_in", 0),
                "tokens_out": extraction_meta.get("tokens_out", 0),
                "molecules_extracted": extraction_meta.get("molecules_count", 0),
                "experiments_extracted": extraction_meta.get("experiments_count", 0),
                "results_extracted": extraction_meta.get("results_count", 0)
            })
            mol_count = len(extraction.get("molecules") or [])
            exp_count = len(extraction.get("experiments") or [])
            logger.emit_progress("OPUS", "end", doc_index=doc_index, doc_total=doc_total,
                                stats={"molecules": mol_count, "experiments": exp_count})

            # Match figure-extracted SMILES to Opus-extracted molecules
            if figure_compounds:
                opus_molecules = extraction.get("molecules") or []
                print(f"  [DEBUG] Figure matching input:")
                print(f"    - Figure compounds: {len(figure_compounds)}")
                print(f"    - Opus molecules: {len(opus_molecules)}")
                print(f"    - Figure compound names: {[c.get('name', '<no name>') for c in figure_compounds[:5]]}{'...' if len(figure_compounds) > 5 else ''}")
                print(f"    - Opus molecule IDs: {[m.get('molecule_id', '<no id>') for m in opus_molecules[:5]]}{'...' if len(opus_molecules) > 5 else ''}")

                molecules, matched_count = match_figure_compounds_to_molecules(
                    figure_compounds,
                    opus_molecules,
                    bundle_dir=bundle_dir
                )
                extraction["molecules"] = molecules
                print(f"  [DEBUG] Figure matching result: {matched_count} matches")
                if matched_count > 0:
                    print(f"  Matched {matched_count} figure-derived SMILES to molecules")

            _write_bundle_file(bundle_dir, "extraction_current.json", extraction)
            extraction = _sanitize_foreign_keys(extraction, logger)
            _upsert_extraction_into_db(conn, doc_id, extraction)

            # Stage 4: GPT Audit
            audit_json = None
            if openai_key and auditor_model:
                logger.emit_progress("AUDIT", "start", doc_index=doc_index, doc_total=doc_total)
                stage_start = time.time()
                audit_json = run_auditor(
                    openai_key=openai_key, model=auditor_model,
                    paper_md=paper_md, extraction=extraction,
                    logger=logger
                )
                audit_meta = audit_json.pop("_meta", {})
                stage_time = time.time() - stage_start

                _write_bundle_file(bundle_dir, "audit_gpt52.json", audit_json)

                logger.log_stage("Stage 4: GPT-5.2 Audit", {
                    "status": "success",
                    "time": stage_time,
                    "items_audited": audit_meta.get("items_audited", 0),
                    "verdicts": audit_meta.get("verdicts", {})
                })
                logger.emit_progress("AUDIT", "end", doc_index=doc_index, doc_total=doc_total,
                                    stats={"audited": audit_meta.get("items_audited", 0)})

                # Log warnings for ambiguous/rejected items
                verdicts = audit_meta.get("verdicts", {})
                if verdicts.get("AMBIGUOUS", 0) > 0:
                    logger.log_warning(
                        f"{verdicts.get('AMBIGUOUS')} items marked AMBIGUOUS",
                        stage="Audit"
                    )
                if verdicts.get("REJECT", 0) > 0:
                    logger.log_warning(
                        f"{verdicts.get('REJECT')} items marked REJECT",
                        stage="Audit"
                    )

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

                # Stage 5: Auto-repair
                logger.emit_progress("REPAIR", "start", doc_index=doc_index, doc_total=doc_total)
                stage_start = time.time()
                repair_report = auto_repair(
                    conn=conn, doc_id=doc_id, bundle_dir=bundle_dir,
                    paper_md=paper_md, extraction=extraction, audit_json=audit_json,
                    anthropic_key=anthropic_key, opus_model=primary_model,
                    max_repairs=25, logger=logger
                )
                repair_meta = repair_report.get("_meta", {})
                stage_time = time.time() - stage_start

                _write_bundle_file(bundle_dir, "repair_report.json", repair_report)
                extraction = repair_report["extraction"]

                logger.log_stage("Stage 5: Auto-Repair", {
                    "status": "success",
                    "time": stage_time,
                    "repairs_attempted": repair_meta.get("attempted", 0),
                    "repairs_applied": repair_meta.get("applied", 0),
                    "repairs_failed": repair_meta.get("failed", 0)
                })
                logger.emit_progress("REPAIR", "end", doc_index=doc_index, doc_total=doc_total,
                                    stats={"repaired": repair_meta.get("applied", 0)})
            else:
                logger.log_stage("Stage 4: GPT-5.2 Audit", {
                    "status": "skipped",
                    "reason": "No OpenAI API key provided"
                })
                logger.log_stage("Stage 5: Auto-Repair", {
                    "status": "skipped",
                    "reason": "No audit results to repair"
                })

            # Stage 6: Gap Hunt
            gaps_json = None
            if gemini_key and gap_model:
                logger.emit_progress("GAP", "start", doc_index=doc_index, doc_total=doc_total)
                stage_start = time.time()
                gaps_json = run_gap_hunter(
                    gemini_key=gemini_key, model=gap_model,
                    paper_md=paper_md, extraction=extraction,
                    bundle_dir=bundle_dir,
                    logger=logger
                )
                gap_meta = gaps_json.pop("_meta", {})
                stage_time = time.time() - stage_start

                _write_bundle_file(bundle_dir, "gaps_gemini.json", gaps_json)

                logger.log_stage("Stage 6: Gemini Gap Hunt", {
                    "status": "success",
                    "time": stage_time,
                    "gaps_identified": gap_meta.get("gaps_identified", 0),
                    "gap_types": gap_meta.get("gap_types", {})
                })
                gaps_count = len(gaps_json.get("gaps") or [])
                logger.emit_progress("GAP", "end", doc_index=doc_index, doc_total=doc_total,
                                    stats={"gaps": gaps_count})

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
            else:
                logger.log_stage("Stage 6: Gemini Gap Hunt", {
                    "status": "skipped",
                    "reason": "No Google API key provided"
                })

            # Stages 7-8: Gap Resolution Loop
            if gaps_json is not None:
                for round_i in range(max_gap_rounds):
                    # Stage 7: Gap Resolution
                    logger.emit_progress("RESOLVE", "start", doc_index=doc_index, doc_total=doc_total)
                    stage_start = time.time()
                    resolve_out = resolve_gaps_with_targeted_opus(
                        anthropic_key=anthropic_key,
                        opus_model=primary_model,
                        paper_md=paper_md,
                        extraction=extraction,
                        gaps_json=gaps_json,
                        bundle_dir=bundle_dir,
                        max_targets=10,
                        logger=logger
                    )
                    resolve_meta = resolve_out.get("_meta", {})
                    extraction = resolve_out["extraction"]
                    stage_time = time.time() - stage_start

                    _write_bundle_file(bundle_dir, f"extraction_after_gap_round_{round_i+1}.json", extraction)
                    extraction = _sanitize_foreign_keys(extraction, logger)
                    _upsert_extraction_into_db(conn, doc_id, extraction)

                    logger.log_stage(f"Stage 7: Gap Resolution (Round {round_i+1})", {
                        "status": "success",
                        "time": stage_time,
                        "gaps_resolved": resolve_meta.get("gaps_resolved", 0),
                        "new_molecules": resolve_meta.get("new_molecules", 0),
                        "new_experiments": resolve_meta.get("new_experiments", 0),
                        "new_results": resolve_meta.get("new_results", 0)
                    })
                    logger.emit_progress("RESOLVE", "end", doc_index=doc_index, doc_total=doc_total,
                                        stats={"resolved": resolve_meta.get("gaps_resolved", 0)})

                    # Stage 8: Re-audit after gap additions
                    if openai_key and auditor_model:
                        stage_start = time.time()
                        audit2 = run_auditor(
                            openai_key=openai_key, model=auditor_model,
                            paper_md=paper_md, extraction=extraction,
                            logger=logger
                        )
                        audit2_meta = audit2.pop("_meta", {})
                        stage_time = time.time() - stage_start

                        _write_bundle_file(bundle_dir, f"audit_after_gap_round_{round_i+1}.json", audit2)

                        logger.log_stage(f"Stage 8: Re-Audit (Round {round_i+1})", {
                            "status": "success",
                            "time": stage_time,
                            "new_issues_found": audit2_meta.get("items_audited", 0) - audit2_meta.get("verdicts", {}).get("SUPPORTED", 0)
                        })

                        repair2 = auto_repair(
                            conn=conn, doc_id=doc_id, bundle_dir=bundle_dir,
                            paper_md=paper_md, extraction=extraction, audit_json=audit2,
                            anthropic_key=anthropic_key, opus_model=primary_model,
                            max_repairs=25, logger=logger
                        )
                        _write_bundle_file(bundle_dir, f"repair_after_gap_round_{round_i+1}.json", repair2)
                        extraction = repair2["extraction"]

                    # Re-run gap hunter
                    if gemini_key and gap_model:
                        gaps_json = run_gap_hunter(
                            gemini_key=gemini_key, model=gap_model,
                            paper_md=paper_md, extraction=extraction,
                            bundle_dir=bundle_dir,
                            logger=logger
                        )
                        gaps_json.pop("_meta", None)
                        _write_bundle_file(bundle_dir, f"gaps_after_round_{round_i+1}.json", gaps_json)

            # Stage 9: SMILES Lookup
            logger.emit_progress("SMILES", "start", doc_index=doc_index, doc_total=doc_total)
            stage_start = time.time()
            molecules = extraction.get("molecules") or []
            smiles_before = sum(1 for m in molecules if m.get("smiles"))

            if molecules:
                enrich_molecules_with_smiles(molecules, logger=logger, delay=0.2)

            smiles_after = sum(1 for m in molecules if m.get("smiles"))
            smiles_found = smiles_after - smiles_before
            stage_time = time.time() - stage_start

            logger.log_stage("Stage 9: SMILES Lookup", {
                "status": "success",
                "time": stage_time,
                "molecules_processed": len(molecules),
                "smiles_found": smiles_found,
                "smiles_coverage": f"{smiles_after}/{len(molecules)}"
            })
            logger.emit_progress("SMILES", "end", doc_index=doc_index, doc_total=doc_total,
                                stats={"found": smiles_found, "total": len(molecules)})

            _write_bundle_file(bundle_dir, "extraction_with_smiles.json", extraction)

            # Stage 10: SMILES Validation (RDKit validation and property enrichment)
            logger.emit_progress("VALIDATE", "start", doc_index=doc_index, doc_total=doc_total)
            stage_start = time.time()

            validation_stats = validate_and_enrich_smiles(
                extraction.get("molecules") or [],
                compute_properties=options.get("smiles_validation", {}).get("compute_properties", True)
            )
            stage_time = time.time() - stage_start

            logger.log_stage("Stage 10: SMILES Validation", {
                "status": "success",
                "time": stage_time,
                "with_smiles": validation_stats.get("with_smiles", 0),
                "valid_smiles": validation_stats.get("valid_smiles", 0),
                "invalid_smiles": validation_stats.get("invalid_smiles", 0),
                "properties_computed": validation_stats.get("properties_computed", 0)
            })
            logger.emit_progress("VALIDATE", "end", doc_index=doc_index, doc_total=doc_total,
                                stats={"valid": validation_stats.get("valid_smiles", 0),
                                      "invalid": validation_stats.get("invalid_smiles", 0)})

            _write_bundle_file(bundle_dir, "extraction_validated.json", extraction)

            # Stage 11: Export
            logger.emit_progress("EXPORT", "start", doc_index=doc_index, doc_total=doc_total)
            stage_start = time.time()
            mol_count = len(extraction.get("molecules") or [])
            exp_count = len(extraction.get("experiments") or [])
            res_count = len(extraction.get("results") or [])

            if extraction.get("molecules") or extraction.get("experiments") or extraction.get("results"):
                export_jsonl(out, doc_id, extraction)

                # Create per-document Excel workbook
                paper_title = meta.get("title") or pdf.stem
                wb = create_review_workbook(extraction, paper_title=paper_title)
                excel_path = bundle_dir / f"{doc_id}_review.xlsx"
                wb.save(excel_path)

                stage_time = time.time() - stage_start

                logger.log_stage("Stage 11: Export", {
                    "status": "success",
                    "time": stage_time,
                    "files_created": {
                        f"{doc_id}_molecules.jsonl": f"{mol_count} records",
                        f"{doc_id}_experiments.jsonl": f"{exp_count} records",
                        f"{doc_id}_results.jsonl": f"{res_count} records",
                        f"{doc_id}_dataset.jsonl": f"{mol_count + exp_count + res_count} records",
                        f"{doc_id}_review.xlsx": "Excel workbook"
                    }
                })
                logger.emit_progress("EXPORT", "end", doc_index=doc_index, doc_total=doc_total)
            else:
                logger.log_warning(f"Skipping export for {doc_id}: no data in extraction", stage="Export")
                logger.log_stage("Stage 11: Export", {
                    "status": "skipped",
                    "reason": "No data in extraction"
                })
                logger.emit_progress("EXPORT", "end", doc_index=doc_index, doc_total=doc_total)

            # Add to extraction summary
            logger.add_extraction_summary(
                extraction.get("molecules") or [],
                extraction.get("experiments") or [],
                extraction.get("results") or [],
                doc_id
            )

            # Collect for combined export
            paper_title = meta.get("title") or pdf.stem
            all_extractions.append({
                "extraction": extraction,
                "paper_title": paper_title,
                "doc_id": doc_id
            })

            processed.append(doc_id)
            logger.end_document("success")

        except Exception as e:
            error_msg = str(e)
            errors.append({"pdf": str(pdf), "error": error_msg})
            logger.log_error(error_msg, stage="Pipeline", exception=e)
            logger.end_document("failed")

    # Get database stats
    db_stats = _get_db_stats(conn)
    logger.set_db_stats(db_stats)

    # Create combined Excel workbook if we have extractions
    combined_excel_path = None
    if all_extractions:
        combined_excel_path = out / "combined_dataset.xlsx"
        export_combined_workbook(all_extractions, combined_excel_path, logger=logger)
        logger.log_stage("Combined Export", {
            "status": "success",
            "papers_combined": len(all_extractions),
            "output_file": str(combined_excel_path)
        })

    # Compute total counts from all extractions
    total_molecules = sum(len(ext["extraction"].get("molecules") or []) for ext in all_extractions)
    total_experiments = sum(len(ext["extraction"].get("experiments") or []) for ext in all_extractions)
    total_results = sum(len(ext["extraction"].get("results") or []) for ext in all_extractions)

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
        "notes": f"Processed {len(processed)} PDFs; errors={len(errors)}; gap_rounds={options.get('max_gap_rounds', 2)}",
    }
    insert_run(conn, run_row)
    conn.close()

    # Finalize logger and get log file path
    log_file = logger.finalize()

    return {
        "run": run_row,
        "documents_processed": processed,
        "errors": errors,
        "log_file": log_file,
        "combined_excel": str(combined_excel_path) if combined_excel_path else None,
        "total_molecules": total_molecules,
        "total_experiments": total_experiments,
        "total_results": total_results
    }
