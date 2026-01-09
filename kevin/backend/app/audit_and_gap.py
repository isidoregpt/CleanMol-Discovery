import json
from typing import Dict, Any, List
from .llm_openai import call_openai_responses, extract_output_text
from .llm_gemini import call_gemini_generate_content, extract_text as gemini_text
from .json_utils import parse_json_strict
from .prompts_audit import AUDIT_INSTRUCTIONS
from .prompts_gap import GAP_HUNTER_PROMPT_TEMPLATE

AUDIT_BATCH_SIZE = 12

def _build_audit_batch(molecules: List, experiments: List, results: List) -> List[Dict]:
    """Build a list of items to audit with their type info."""
    items = []
    for m in molecules:
        items.append({"type": "molecule", "id_key": "molecule_id", "data": m})
    for e in experiments:
        items.append({"type": "experiment", "id_key": "experiment_id", "data": e})
    for r in results:
        items.append({"type": "result", "id_key": "result_id", "data": r})
    return items

def _batch_items(items: List, batch_size: int) -> List[List]:
    """Split items into batches."""
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

def _run_single_audit_batch(*, openai_key: str, model: str, paper_md: str, batch: List[Dict], logger=None) -> Dict:
    """Run audit on a single batch of items."""
    batch_extraction = {"molecules": [], "experiments": [], "results": []}
    for item in batch:
        if item["type"] == "molecule":
            batch_extraction["molecules"].append(item["data"])
        elif item["type"] == "experiment":
            batch_extraction["experiments"].append(item["data"])
        elif item["type"] == "result":
            batch_extraction["results"].append(item["data"])

    prompt = (
        "Paper Markdown:\n---\n" + paper_md + "\n---\n\n"
        "Extraction JSON:\n---\n" + json.dumps(batch_extraction, ensure_ascii=False) + "\n---"
    )

    resp, _meta = call_openai_responses(
        api_key=openai_key, model=model, instructions=AUDIT_INSTRUCTIONS,
        input_text=prompt, reasoning_effort="high", max_output_tokens=6000
    )
    out = extract_output_text(resp)
    return parse_json_strict(out)

def run_auditor(*, openai_key: str, model: str, paper_md: str, extraction: dict, logger=None) -> dict:
    """Run audit in batches to avoid token limits."""
    molecules = extraction.get("molecules") or []
    experiments = extraction.get("experiments") or []
    results = extraction.get("results") or []

    all_items = _build_audit_batch(molecules, experiments, results)

    if len(all_items) <= AUDIT_BATCH_SIZE:
        prompt = (
            "Paper Markdown:\n---\n" + paper_md + "\n---\n\n"
            "Extraction JSON:\n---\n" + json.dumps(extraction, ensure_ascii=False) + "\n---"
        )
        resp, _meta = call_openai_responses(
            api_key=openai_key, model=model, instructions=AUDIT_INSTRUCTIONS,
            input_text=prompt, reasoning_effort="high", max_output_tokens=6000
        )
        out = extract_output_text(resp)
        return parse_json_strict(out)

    batches = _batch_items(all_items, AUDIT_BATCH_SIZE)
    all_audits = []

    for batch in batches:
        try:
            batch_result = _run_single_audit_batch(
                openai_key=openai_key, model=model, paper_md=paper_md, batch=batch, logger=logger
            )
            all_audits.extend(batch_result.get("audits") or [])
        except Exception as e:
            print(f"Audit batch failed: {e}")
            continue

    return {"audits": all_audits}


def run_gap_hunter(*, gemini_key: str, model: str, paper_md: str, extraction: dict, logger=None) -> dict:
    prompt = GAP_HUNTER_PROMPT_TEMPLATE.format(
        paper_md=paper_md, extraction_json=json.dumps(extraction, ensure_ascii=False)
    )
    resp, _meta = call_gemini_generate_content(api_key=gemini_key, model=model, prompt=prompt)
    out = gemini_text(resp)
    return parse_json_strict(out)
