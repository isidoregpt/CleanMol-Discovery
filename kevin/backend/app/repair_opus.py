import json
from .llm_anthropic import call_anthropic_messages, extract_text_from_response
from .json_utils import parse_json_strict
from .prompts_repair import REPAIR_SYSTEM, REPAIR_USER_TEMPLATE

def repair_entity_with_opus(*, anthropic_key: str, model: str, entity_type: str, entity: dict,
                            verdict: str, issues: list, page_slice_md: str) -> dict:
    user = REPAIR_USER_TEMPLATE.format(
        entity_type=entity_type,
        entity_json=json.dumps(entity, ensure_ascii=False, indent=2),
        verdict=verdict,
        issues_json=json.dumps(issues, ensure_ascii=False, indent=2),
        page_slice_md=page_slice_md
    )
    resp = call_anthropic_messages(
        api_key=anthropic_key, model=model, system=REPAIR_SYSTEM, user=user,
        max_tokens=2500, temperature=0.1
    )
    text = extract_text_from_response(resp)
    return parse_json_strict(text)
