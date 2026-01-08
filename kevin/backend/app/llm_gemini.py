import requests
from typing import Dict, Any

def call_gemini_generate_content(*, api_key: str, model: str, prompt: str,
                                 max_output_tokens: int = 4096, temperature: float = 0.2) -> Dict[str, Any]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_output_tokens},
    }
    r = requests.post(url, headers=headers, json=payload, timeout=300)
    r.raise_for_status()
    return r.json()

def extract_text(resp: Dict[str, Any]) -> str:
    cands = resp.get("candidates") or []
    if not cands:
        return ""
    parts = ((cands[0].get("content") or {}).get("parts")) or []
    return "".join([p.get("text","") for p in parts if "text" in p]).strip()
