import requests
import time
from typing import Dict, Any, Tuple

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


def call_openai_responses(*, api_key: str, model: str, instructions: str, input_text: str,
                          reasoning_effort: str = "high", max_output_tokens: int = 6000) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Call OpenAI Chat Completions API.

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

    messages = [
        {"role": "developer", "content": instructions},
        {"role": "user", "content": input_text}
    ]

    payload = {
        "model": model,
        "messages": messages,
        "max_completion_tokens": max_output_tokens,
        "reasoning_effort": reasoning_effort,
    }

    start_time = time.time()
    r = requests.post(OPENAI_CHAT_URL, headers=headers, json=payload, timeout=300)
    duration = time.time() - start_time

    r.raise_for_status()
    resp = r.json()

    # Extract token usage from response
    usage = resp.get("usage", {})
    metadata = {
        "tokens_in": usage.get("prompt_tokens", 0),
        "tokens_out": usage.get("completion_tokens", 0),
        "duration_sec": round(duration, 2),
        "model": model,
        "endpoint": "/v1/chat/completions",
        "provider": "OpenAI"
    }

    return resp, metadata


def extract_output_text(resp: Dict[str, Any]) -> str:
    """Extract the assistant's response text from chat completions response."""
    choices = resp.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return message.get("content", "").strip()
