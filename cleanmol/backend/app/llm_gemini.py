import requests
import time
from typing import Dict, Any, Tuple, Optional


def call_gemini_generate_content(
    *,
    api_key: str,
    model: str,
    prompt: str,
    max_output_tokens: int = 4096,
    temperature: float = 0.2,
    response_mime_type: Optional[str] = None,
    timeout_sec: int = 300,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Call Gemini generateContent API.

    Returns:
        Tuple of (response_json, metadata) where metadata contains:
        - tokens_in: input token count
        - tokens_out: output token count
        - duration_sec: request duration in seconds
        - model: model used
        - endpoint: API endpoint
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    generation_config: Dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens,
    }
    if response_mime_type:
        generation_config["responseMimeType"] = response_mime_type

    payload: Dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": generation_config,
    }

    start_time = time.time()
    r = requests.post(url, headers=headers, json=payload, timeout=timeout_sec)
    duration = time.time() - start_time

    r.raise_for_status()
    resp = r.json()

    # Extract token usage from response
    usage_metadata = resp.get("usageMetadata", {})
    metadata = {
        "tokens_in": usage_metadata.get("promptTokenCount", 0),
        "tokens_out": usage_metadata.get("candidatesTokenCount", 0),
        "duration_sec": round(duration, 2),
        "model": model,
        "endpoint": "/generateContent",
        "provider": "Google"
    }

    return resp, metadata


def extract_text(resp: Dict[str, Any]) -> str:
    cands = resp.get("candidates") or []
    if not cands:
        return ""
    parts = ((cands[0].get("content") or {}).get("parts")) or []
    return "".join([p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p]).strip()
