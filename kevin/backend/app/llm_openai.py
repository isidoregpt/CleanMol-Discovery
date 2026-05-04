import requests
import time
from typing import Dict, Any, Tuple

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


def call_openai_responses(*, api_key: str, model: str, instructions: str, input_text: str,
                          reasoning_effort: str = "high", max_output_tokens: int = 6000) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Call the OpenAI Responses API.

    Returns:
        Tuple of (response_json, metadata) where metadata contains:
        - tokens_in: input token count
        - tokens_out: output token count
        - duration_sec: request duration in seconds
        - model: model used
        - endpoint: API endpoint
        - provider: API provider name
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "model": model,
        "instructions": instructions,
        "input": input_text,
        "max_output_tokens": max_output_tokens,
        "text": {"format": {"type": "json_object"}},
    }
    if _supports_reasoning_effort(model):
        payload["reasoning"] = {"effort": reasoning_effort}

    start_time = time.time()
    r = requests.post(OPENAI_RESPONSES_URL, headers=headers, json=payload, timeout=300)
    duration = time.time() - start_time

    r.raise_for_status()
    resp = r.json()

    # Extract token usage from response
    usage = resp.get("usage", {})
    metadata = {
        "tokens_in": usage.get("input_tokens", 0),
        "tokens_out": usage.get("output_tokens", 0),
        "duration_sec": round(duration, 2),
        "model": model,
        "endpoint": "/v1/responses",
        "provider": "OpenAI"
    }

    return resp, metadata


def _supports_reasoning_effort(model: str) -> bool:
    model_id = (model or "").lower()
    return model_id.startswith(("gpt-5", "o1", "o3", "o4", "gpt-oss"))


def extract_output_text(resp: Dict[str, Any]) -> str:
    """Extract assistant text from a Responses API response."""
    if resp.get("output_text"):
        return str(resp["output_text"]).strip()

    chunks = []
    for item in resp.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text":
                chunks.append(content.get("text", ""))
    return "".join(chunks).strip()
