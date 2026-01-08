import json
from .llm_openai import call_openai_responses, extract_output_text
from .llm_gemini import call_gemini_generate_content, extract_text as gemini_text
from .json_utils import parse_json_strict
from .prompts_audit import AUDIT_INSTRUCTIONS
from .prompts_gap import GAP_HUNTER_PROMPT_TEMPLATE

def run_auditor(*, openai_key: str, model: str, paper_md: str, extraction: dict) -> dict:
    prompt = (
        "Paper Markdown:\n---\n" + paper_md + "\n---\n\n"
        "Extraction JSON:\n---\n" + json.dumps(extraction, ensure_ascii=False) + "\n---"
    )
    resp = call_openai_responses(
        api_key=openai_key, model=model, instructions=AUDIT_INSTRUCTIONS,
        input_text=prompt, reasoning_effort="high", max_output_tokens=6000
    )
    out = extract_output_text(resp)
    return parse_json_strict(out)

def run_gap_hunter(*, gemini_key: str, model: str, paper_md: str, extraction: dict) -> dict:
    prompt = GAP_HUNTER_PROMPT_TEMPLATE.format(
        paper_md=paper_md, extraction_json=json.dumps(extraction, ensure_ascii=False)
    )
    resp = call_gemini_generate_content(api_key=gemini_key, model=model, prompt=prompt)
    out = gemini_text(resp)
    return parse_json_strict(out)
