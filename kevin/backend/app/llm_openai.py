import requests
from typing import Dict, Any

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

def call_openai_responses(*, api_key: str, model: str, instructions: str, input_text: str,
                          reasoning_effort: str = "high", max_output_tokens: int = 6000) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "instructions": instructions,
        "input": input_text,
        "reasoning": {"effort": reasoning_effort},
        "max_output_tokens": max_output_tokens,
    }
    r = requests.post(OPENAI_RESPONSES_URL, headers=headers, json=payload, timeout=300)
    r.raise_for_status()
    return r.json()

def extract_output_text(resp: Dict[str, Any]) -> str:
    if isinstance(resp.get("output_text"), str):
        return resp["output_text"].strip()
    out = []
    for item in resp.get("output", []) or []:
        if item.get("type") == "message":
            for c in item.get("content", []) or []:
                if c.get("type") == "output_text":
                    out.append(c.get("text",""))
    return "".join(out).strip()
