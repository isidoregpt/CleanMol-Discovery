import json
from pathlib import Path
from .prompts_opus import OPUS_SYSTEM, OPUS_USER_TEMPLATE
from .llm_anthropic import call_anthropic_messages, extract_text_from_response
from .json_utils import parse_json_strict

def run_opus_extraction(*, anthropic_key: str, model: str, bundle_dir: Path, paper_md_path: Path) -> dict:
    paper_md = paper_md_path.read_text(encoding="utf-8")
    user_prompt = OPUS_USER_TEMPLATE.format(paper_md=paper_md)
    resp = call_anthropic_messages(
        api_key=anthropic_key, model=model, system=OPUS_SYSTEM, user=user_prompt,
        max_tokens=8192, temperature=0.2
    )
    text = extract_text_from_response(resp)
    data = parse_json_strict(text)

    (bundle_dir / "extraction_opus.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (bundle_dir / "extraction_opus_raw.txt").write_text(text, encoding="utf-8")
    return data
