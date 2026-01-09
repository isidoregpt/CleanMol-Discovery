import json
import re
from typing import Any, Dict

def parse_json_strict(text: str) -> Dict[str, Any]:
    """
    Parse JSON from model output, handling cases where models include
    reasoning text, markdown code blocks, or other non-JSON content.
    """
    text = text.strip()

    # Fast path: direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # Remove markdown code blocks if present
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    # Try parsing again after removing code blocks
    try:
        return json.loads(text)
    except Exception:
        pass

    # Find JSON object - look for outermost balanced braces
    start = text.find('{')
    if start == -1:
        raise ValueError("No JSON object found in model output.")

    # Find matching closing brace
    depth = 0
    end = -1
    in_string = False
    escape = False

    for i in range(start, len(text)):
        c = text[i]

        if escape:
            escape = False
            continue

        if c == '\\' and in_string:
            escape = True
            continue

        if c == '"' and not escape:
            in_string = not in_string
            continue

        if in_string:
            continue

        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end == -1:
        raise ValueError("No complete JSON object found in model output.")

    candidate = text[start:end]

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}")
