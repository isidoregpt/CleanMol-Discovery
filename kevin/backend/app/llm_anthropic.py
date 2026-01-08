import requests
import time
from typing import Dict, Any, Tuple

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


def call_anthropic_messages(*, api_key: str, model: str, system: str, user: str,
                            max_tokens: int = 8192, temperature: float = 0.2) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Call Anthropic Messages API.

    Returns:
        Tuple of (response_json, metadata) where metadata contains:
        - tokens_in: input token count
        - tokens_out: output token count
        - duration_sec: request duration in seconds
        - model: model used
        - endpoint: API endpoint
    """
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }

    start_time = time.time()
    r = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=300)
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
        "endpoint": "/v1/messages",
        "provider": "Anthropic"
    }

    return resp, metadata


def extract_text_from_response(resp: Dict[str, Any]) -> str:
    blocks = resp.get("content", [])
    return "".join([b.get("text", "") for b in blocks if b.get("type") == "text"]).strip()
