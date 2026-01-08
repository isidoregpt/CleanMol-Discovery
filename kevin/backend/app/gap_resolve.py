import json
import uuid
from typing import List, Dict, Any
from pathlib import Path
from .context_slice import slice_pages
from .llm_anthropic import call_anthropic_messages, extract_text_from_response
from .json_utils import parse_json_strict
from .prompts_targeted import TARGETED_SYSTEM, TARGETED_USER_TEMPLATE

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

    merged_mols = (merged.get("molecules") or []) + (additions.get("molecules") or [])
    merged_exps = (merged.get("experiments") or []) + (additions.get("experiments") or [])
    merged_res  = (merged.get("results") or []) + (additions.get("results") or [])

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
) -> dict:
    gaps = (gaps_json.get("gaps") or [])
    actionable = [g for g in gaps if g.get("page") is not None][:max_targets]

    updated = dict(extraction)
    resolutions = []

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

        resp = call_anthropic_messages(
            api_key=anthropic_key,
            model=opus_model,
            system=TARGETED_SYSTEM,
            user=user,
            max_tokens=4000,
            temperature=0.15,
        )
        text = extract_text_from_response(resp)
        out = parse_json_strict(text)
        adds = (out.get("additions") or {})

        updated = merge_additions(updated, adds)
        resolutions.append({"gap": g, "notes": out.get("notes")})

    (bundle_dir / "gap_resolutions_opus.json").write_text(
        json.dumps({"resolutions": resolutions, "extraction_after_gap_resolution": updated}, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    return {"extraction": updated, "resolutions": resolutions}
