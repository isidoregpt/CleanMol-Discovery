import json
import re
from typing import Any, Dict

def parse_json_strict(text: str) -> Dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON object found in model output.")
    candidate = m.group(0)
    return json.loads(candidate)
