import json
from typing import Optional
from .llm_anthropic import call_anthropic_messages, extract_text_from_response
from .json_utils import parse_json_strict
from .prompts_repair import REPAIR_SYSTEM, REPAIR_USER_TEMPLATE
from .logger import PipelineLogger


def repair_entity_with_opus(*, anthropic_key: str, model: str, entity_type: str, entity: dict,
                            verdict: str, issues: list, page_slice_md: str,
                            logger: Optional[PipelineLogger] = None) -> dict:
    """
    Repair a single entity using Opus.

    Returns:
        dict with repaired entity and notes
    """
    user = REPAIR_USER_TEMPLATE.format(
        entity_type=entity_type,
        entity_json=json.dumps(entity, ensure_ascii=False, indent=2),
        verdict=verdict,
        issues_json=json.dumps(issues, ensure_ascii=False, indent=2),
        page_slice_md=page_slice_md
    )

    resp, api_meta = call_anthropic_messages(
        api_key=anthropic_key, model=model, system=REPAIR_SYSTEM, user=user,
        max_tokens=2500, temperature=0.1
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
    return parse_json_strict(text)
