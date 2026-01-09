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


def _ensure_experiment_exists(extraction: dict, experiment_id: str) -> dict:
    """Ensure an experiment exists, create placeholder if not."""
    if not experiment_id:
        return extraction
    existing_ids = {e.get("experiment_id") for e in (extraction.get("experiments") or [])}
    if experiment_id not in existing_ids:
        placeholder = {
            "experiment_id": experiment_id,
            "organism": None,
            "strain": None,
            "assay_type": "unknown",
            "conditions": None,
            "exposure_protocol": None,
            "evidence": {"kind": "snippet", "page": 1, "snippet": "Auto-generated placeholder for gap resolution"}
        }
        if "experiments" not in extraction:
            extraction["experiments"] = []
        extraction["experiments"].append(placeholder)
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
    merged = dict(extraction)

    # Ensure experiments exist for all results before merging
    for res in (additions.get("results") or []):
        exp_id = res.get("experiment_id")
        if exp_id:
            merged = _ensure_experiment_exists(merged, exp_id)

    merged_mols = (merged.get("molecules") or []) + (additions.get("molecules") or [])
    merged_exps = (merged.get("experiments") or []) + (additions.get("experiments") or [])
    merged_res = (merged.get("results") or []) + (additions.get("results") or [])

    merged["molecules"] = _dedupe_by_id(merged_mols, "molecule_id")
    merged["experiments"] = _dedupe_by_id(merged_exps, "experiment_id")
    merged["results"] = _dedupe_by_id(merged_res, "result_id")
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
            max_tokens=4000,
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
