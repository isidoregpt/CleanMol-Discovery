import json
import time
from typing import Optional
from .llm_openai import call_openai_responses, extract_output_text
from .llm_gemini import call_gemini_generate_content, extract_text as gemini_text
from .json_utils import parse_json_strict
from .prompts_audit import AUDIT_INSTRUCTIONS
from .prompts_gap import GAP_HUNTER_PROMPT_TEMPLATE
from .logger import PipelineLogger


def run_auditor(*, openai_key: str, model: str, paper_md: str, extraction: dict,
                logger: Optional[PipelineLogger] = None) -> dict:
    """
    Run GPT audit on extraction results.

    Returns:
        dict with audit results
    """
    start_time = time.time()

    prompt = (
        "Paper Markdown:\n---\n" + paper_md + "\n---\n\n"
        "Extraction JSON:\n---\n" + json.dumps(extraction, ensure_ascii=False) + "\n---"
    )

    resp, api_meta = call_openai_responses(
        api_key=openai_key, model=model, instructions=AUDIT_INSTRUCTIONS,
        input_text=prompt, reasoning_effort="high", max_output_tokens=6000
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

    out = extract_output_text(resp)
    data = parse_json_strict(out)

    elapsed = time.time() - start_time

    # Count verdicts
    audits = data.get("audits") or []
    verdicts = {"SUPPORTED": 0, "AMBIGUOUS": 0, "REJECT": 0}
    for a in audits:
        v = a.get("verdict", "").upper()
        if v in verdicts:
            verdicts[v] += 1

    # Add metadata for logging
    data["_meta"] = {
        "time": elapsed,
        "tokens_in": api_meta["tokens_in"],
        "tokens_out": api_meta["tokens_out"],
        "items_audited": len(audits),
        "verdicts": verdicts
    }

    return data


def run_gap_hunter(*, gemini_key: str, model: str, paper_md: str, extraction: dict,
                   logger: Optional[PipelineLogger] = None) -> dict:
    """
    Run Gemini gap hunter to find missed data.

    Returns:
        dict with gap suggestions
    """
    start_time = time.time()

    prompt = GAP_HUNTER_PROMPT_TEMPLATE.format(
        paper_md=paper_md, extraction_json=json.dumps(extraction, ensure_ascii=False)
    )

    resp, api_meta = call_gemini_generate_content(api_key=gemini_key, model=model, prompt=prompt)

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

    out = gemini_text(resp)
    data = parse_json_strict(out)

    elapsed = time.time() - start_time

    # Count gap types
    gaps = data.get("gaps") or []
    gap_types = {}
    for g in gaps:
        kind = g.get("kind", "unknown")
        gap_types[kind] = gap_types.get(kind, 0) + 1

    # Add metadata for logging
    data["_meta"] = {
        "time": elapsed,
        "tokens_in": api_meta["tokens_in"],
        "tokens_out": api_meta["tokens_out"],
        "gaps_identified": len(gaps),
        "gap_types": gap_types
    }

    return data
