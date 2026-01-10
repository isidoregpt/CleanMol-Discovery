import json
import time
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
from .context_slice import slice_pages
from .llm_anthropic import call_anthropic_messages, extract_text_from_response
from .json_utils import parse_json_strict
from .prompts_targeted import TARGETED_SYSTEM, TARGETED_USER_TEMPLATE
from .logger import PipelineLogger


def _sanitize_foreign_keys(extraction: dict) -> dict:
    """
    Ensure all results have valid experiment_id and molecule_id references.
    Invalid references are set to None and annotated with orphan metadata.
    This prevents FK constraint failures without inventing fake parent records.
    """
    existing_exp_ids = {e.get("experiment_id") for e in (extraction.get("experiments") or []) if e.get("experiment_id")}
    existing_mol_ids = {m.get("molecule_id") for m in (extraction.get("molecules") or []) if m.get("molecule_id")}

    for result in (extraction.get("results") or []):
        if "_meta" not in result:
            result["_meta"] = {}

        exp_id = result.get("experiment_id")
        mol_id = result.get("molecule_id")

        if exp_id and exp_id not in existing_exp_ids:
            result["_meta"]["orphan_experiment"] = True
            result["_meta"]["original_experiment_id"] = exp_id
            result["experiment_id"] = None

        if mol_id and mol_id not in existing_mol_ids:
            result["_meta"]["orphan_molecule"] = True
            result["_meta"]["original_molecule_id"] = mol_id
            result["molecule_id"] = None

    return extraction


def _dedupe_by_id(items: List[dict], key: str) -> List[dict]:
    seen = set()
    out = []
    for it in items:
        v = it.get(key)
        if not v:
            v = f"autogen:{uuid.uuid4()}"
            it[key] = v
        if v in seen:
            continue
        seen.add(v)
        out.append(it)
    return out


def merge_additions(extraction: dict, additions: dict) -> dict:
    """
    Merge additions into extraction, deduplicating by ID.
    PRESERVES existing SMILES data when merging duplicates.
    Sanitizes foreign keys to null orphan references instead of creating placeholders.
    """
    # Build lookup of existing molecules with their SMILES
    existing_mol_smiles = {}
    for mol in (extraction.get("molecules") or []):
        mol_id = mol.get("molecule_id")
        if mol_id and mol.get("smiles"):
            existing_mol_smiles[mol_id] = {
                "smiles": mol.get("smiles"),
                "smiles_source": mol.get("smiles_source"),
                "smiles_valid": mol.get("smiles_valid"),
                "smiles_confidence": mol.get("smiles_confidence")
            }

    # DEBUG: Show what we're preserving
    if existing_mol_smiles:
        print(f"  [DEBUG merge_additions] Backing up SMILES for {len(existing_mol_smiles)} molecules: {list(existing_mol_smiles.keys())}")

    merged = dict(extraction)

    merged_mols = (merged.get("molecules") or []) + (additions.get("molecules") or [])
    merged_exps = (merged.get("experiments") or []) + (additions.get("experiments") or [])
    merged_res = (merged.get("results") or []) + (additions.get("results") or [])

    merged["molecules"] = _dedupe_by_id(merged_mols, "molecule_id")
    merged["experiments"] = _dedupe_by_id(merged_exps, "experiment_id")
    merged["results"] = _dedupe_by_id(merged_res, "result_id")

    # RESTORE SMILES data that may have been lost during deduplication
    restored_count = 0
    for mol in merged["molecules"]:
        mol_id = mol.get("molecule_id")
        if mol_id in existing_mol_smiles and not mol.get("smiles"):
            smiles_data = existing_mol_smiles[mol_id]
            mol["smiles"] = smiles_data["smiles"]
            mol["smiles_source"] = smiles_data.get("smiles_source")
            mol["smiles_valid"] = smiles_data.get("smiles_valid")
            mol["smiles_confidence"] = smiles_data.get("smiles_confidence")
            restored_count += 1

    # DEBUG: Show final SMILES count
    final_smiles_count = sum(1 for m in merged["molecules"] if m.get("smiles"))
    print(f"  [DEBUG merge_additions] After merge: {final_smiles_count} molecules have SMILES (restored {restored_count})")

    # Sanitize foreign keys to null orphan references instead of inventing placeholders
    merged = _sanitize_foreign_keys(merged)

    return merged


def resolve_gaps_with_targeted_opus(
    *,
    anthropic_key: str,
    opus_model: str,
    paper_md: str,
    extraction: dict,
    gaps_json: dict,
    bundle_dir: Path,
    max_targets: int = 10,
    logger: Optional[PipelineLogger] = None,
) -> dict:
    """
    Resolve gaps with targeted Opus extraction.

    Returns:
        dict with updated extraction and resolutions
    """
    start_time = time.time()

    # DEBUG: Check if extraction has SMILES when we receive it
    incoming_smiles = [(m.get("molecule_id"), m.get("smiles_source"))
                       for m in (extraction.get("molecules") or []) if m.get("smiles")]
    print(f"  [DEBUG resolve_gaps] Received extraction with {len(incoming_smiles)} molecules having SMILES: {[x[0] for x in incoming_smiles]}")

    gaps = (gaps_json.get("gaps") or [])
    actionable = [g for g in gaps if g.get("page") is not None][:max_targets]

    updated = dict(extraction)
    resolutions = []
    new_molecules = 0
    new_experiments = 0
    new_results = 0

    for g in actionable:
        try:
            page = int(g.get("page"))
        except Exception:
            continue

        page_slice_md = slice_pages(paper_md, [page], pad=1)
        user = TARGETED_USER_TEMPLATE.format(
            gaps_json=json.dumps([g], ensure_ascii=False, indent=2),
            extraction_json=json.dumps(updated, ensure_ascii=False),
            page_slice_md=page_slice_md,
        )

        resp, api_meta = call_anthropic_messages(
            api_key=anthropic_key,
            model=opus_model,
            system=TARGETED_SYSTEM,
            user=user,
            max_tokens=8000,
            temperature=0.15,
        )

        # Log API call if logger provided
        if logger:
            logger.log_api_call(
                provider=api_meta["provider"],
                model=api_meta["model"],
                endpoint=api_meta["endpoint"],
                tokens_in=api_meta["tokens_in"],
                tokens_out=api_meta["tokens_out"],
                duration_sec=api_meta["duration_sec"],
                status="success"
            )

        text = extract_text_from_response(resp)
        out = parse_json_strict(text)
        adds = (out.get("additions") or {})

        # Track new additions
        new_molecules += len(adds.get("molecules") or [])
        new_experiments += len(adds.get("experiments") or [])
        new_results += len(adds.get("results") or [])

        updated = merge_additions(updated, adds)
        resolutions.append({"gap": g, "notes": out.get("notes")})

    elapsed = time.time() - start_time

    # DEBUG: Check SMILES count at the end
    outgoing_smiles = [(m.get("molecule_id"), m.get("smiles_source"))
                       for m in (updated.get("molecules") or []) if m.get("smiles")]
    print(f"  [DEBUG resolve_gaps] Returning extraction with {len(outgoing_smiles)} molecules having SMILES: {[x[0] for x in outgoing_smiles]}")

    (bundle_dir / "gap_resolutions_opus.json").write_text(
        json.dumps({"resolutions": resolutions, "extraction_after_gap_resolution": updated}, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return {
        "extraction": updated,
        "resolutions": resolutions,
        "_meta": {
            "time": elapsed,
            "gaps_resolved": len(resolutions),
            "new_molecules": new_molecules,
            "new_experiments": new_experiments,
            "new_results": new_results
        }
    }
