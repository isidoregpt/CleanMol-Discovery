import requests
import time
from typing import Dict, Any, Tuple

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


def call_openai_responses(*, api_key: str, model: str, instructions: str, input_text: str,
                          reasoning_effort: str = "high", max_output_tokens: int = 6000) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Call OpenAI Responses API.

    Returns:
        Tuple of (response_json, metadata) where metadata contains:
        - tokens_in: input token count
        - tokens_out: output token count
        - duration_sec: request duration in seconds
        - model: model used
        - endpoint: API endpoint
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "instructions": instructions,
        "input": input_text,
        "reasoning": {"effort": reasoning_effort},
        "max_output_tokens": max_output_tokens,
    }

    start_time = time.time()
    r = requests.post(OPENAI_RESPONSES_URL, headers=headers, json=payload, timeout=300)
    duration = time.time() - start_time

    r.raise_for_status()
    resp = r.json()

    # Extract token usage from response
    usage = resp.get("usage", {})
    metadata = {
        "tokens_in": usage.get("input_tokens", usage.get("prompt_tokens", 0)),
        "tokens_out": usage.get("output_tokens", usage.get("completion_tokens", 0)),
        "duration_sec": round(duration, 2),
        "model": model,
        "endpoint": "/v1/responses",
        "provider": "OpenAI"
    }

    return resp, metadata


def extract_output_text(resp: Dict[str, Any]) -> str:
    if isinstance(resp.get("output_text"), str):
        return resp["output_text"].strip()
    out = []
    for item in resp.get("output", []) or []:
        if item.get("type") == "message":
            for c in item.get("content", []) or []:
                if c.get("type") == "output_text":
                    out.append(c.get("text", ""))
    return "".join(out).strip()
