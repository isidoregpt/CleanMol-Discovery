import requests
from typing import Dict, Any

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"

def call_openai_responses(*, api_key: str, model: str, instructions: str, input_text: str,
                          reasoning_effort: str = "high", max_output_tokens: int = 6000) -> Dict[str, Any]:
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

    r = requests.post(OPENAI_CHAT_URL, headers=headers, json=payload, timeout=300)
    r.raise_for_status()
    return r.json()

def extract_output_text(resp: Dict[str, Any]) -> str:
    choices = resp.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return message.get("content", "").strip()
