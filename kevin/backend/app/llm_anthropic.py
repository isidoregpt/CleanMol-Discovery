import requests
from typing import Dict, Any

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

def call_anthropic_messages(*, api_key: str, model: str, system: str, user: str,
                            max_tokens: int = 8192, temperature: float = 0.2) -> Dict[str, Any]:
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
    r = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=300)
    r.raise_for_status()
    return r.json()

def extract_text_from_response(resp: Dict[str, Any]) -> str:
    blocks = resp.get("content", [])
    return "".join([b.get("text","") for b in blocks if b.get("type") == "text"]).strip()
