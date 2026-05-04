"""Model defaults and compatibility aliases for the CleanMol pipeline."""

from typing import Dict, Mapping


DEFAULT_MODELS: Dict[str, str] = {
    "primary": "claude-opus-4-7",
    "auditor": "gpt-5.5",
    "gapHunter": "gemini-3.1-pro-preview",
    "figure": "claude-sonnet-4-6",
}

MODEL_DEFAULTS_LAST_VERIFIED = "2026-05-04"

MODEL_DEFAULT_SOURCE_URLS: Dict[str, str] = {
    "anthropic": "https://platform.claude.com/docs/en/about-claude/models/overview",
    "openai": "https://developers.openai.com/api/docs/models",
    "google": "https://ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview",
}


LEGACY_MODEL_ALIASES: Dict[str, str] = {
    "claude-opus-4-5-20251101": DEFAULT_MODELS["primary"],
    "claude-opus-4-20250514": DEFAULT_MODELS["primary"],
    "claude-opus-4-1-20250805": DEFAULT_MODELS["primary"],
    "claude-sonnet-4-5-20250929": DEFAULT_MODELS["figure"],
    "gpt-5.2": DEFAULT_MODELS["auditor"],
    "gpt-5.2-thinking": DEFAULT_MODELS["auditor"],
    "gpt-5.2-2025-12-11": DEFAULT_MODELS["auditor"],
    "gemini-3-pro": DEFAULT_MODELS["gapHunter"],
    "gemini-3-pro-preview": DEFAULT_MODELS["gapHunter"],
}


def normalize_model_id(model_id: str) -> str:
    """Return the configured model id, upgrading known retired ids."""
    value = (model_id or "").strip()
    if not value:
        return value
    return LEGACY_MODEL_ALIASES.get(value, value)


def normalize_models(models: Mapping[str, str] | None) -> Dict[str, str]:
    """Apply defaults and legacy aliases to the model bundle sent by the UI."""
    provided = dict(models or {})
    normalized = dict(DEFAULT_MODELS)

    for key in DEFAULT_MODELS:
        value = provided.get(key)
        if value:
            normalized[key] = normalize_model_id(value)

    return normalized
