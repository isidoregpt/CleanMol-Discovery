import json
import time
from pathlib import Path
from typing import Optional
from .prompts_opus import OPUS_SYSTEM, OPUS_USER_TEMPLATE
from .llm_anthropic import call_anthropic_messages, extract_text_from_response
from .json_utils import parse_json_strict
from .logger import PipelineLogger


def run_opus_extraction(*, anthropic_key: str, model: str, bundle_dir: Path,
                        paper_md_path: Path, logger: Optional[PipelineLogger] = None) -> dict:
    """
    Run Opus extraction on a paper.

    Returns:
        dict with extracted data (molecules, experiments, results)
    """
    start_time = time.time()

    paper_md = paper_md_path.read_text(encoding="utf-8")
    user_prompt = OPUS_USER_TEMPLATE.format(paper_md=paper_md)

    resp, api_meta = call_anthropic_messages(
        api_key=anthropic_key, model=model, system=OPUS_SYSTEM, user=user_prompt,
        max_tokens=16000, temperature=0.2
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
    data = parse_json_strict(text)

    (bundle_dir / "extraction_opus.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (bundle_dir / "extraction_opus_raw.txt").write_text(text, encoding="utf-8")

    elapsed = time.time() - start_time

    # Add metadata for logging
    data["_meta"] = {
        "time": elapsed,
        "tokens_in": api_meta["tokens_in"],
        "tokens_out": api_meta["tokens_out"],
        "molecules_count": len(data.get("molecules") or []),
        "experiments_count": len(data.get("experiments") or []),
        "results_count": len(data.get("results") or [])
    }

    return data
