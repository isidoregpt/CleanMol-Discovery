"""Model defaults, provider refresh, and compatibility aliases."""

from datetime import datetime, timezone
import re
from typing import Any, Dict, Mapping, Optional, Sequence

import requests


DEFAULT_MODELS: Dict[str, str] = {
    "primary": "claude-opus-4-7",
    "auditor": "gpt-5.5",
    "gapHunter": "gemini-3.1-pro-preview",
    "figure": "claude-opus-4-7",
}

MODEL_DEFAULTS_LAST_VERIFIED = "2026-05-04"
MODEL_DEFAULT_MODE = "latest_provider_available"

MODEL_DEFAULT_SOURCE_URLS: Dict[str, str] = {
    "anthropic": "https://platform.claude.com/docs/en/about-claude/models/overview",
    "openai": "https://developers.openai.com/api/docs/models",
    "google": "https://ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview",
}

PROVIDER_MODEL_API_URLS: Dict[str, str] = {
    "anthropic": "https://api.anthropic.com/v1/models",
    "openai": "https://api.openai.com/v1/models",
    "google": "https://generativelanguage.googleapis.com/v1beta/models",
}


LEGACY_MODEL_ALIASES: Dict[str, str] = {
    "claude-opus-4-5-20251101": DEFAULT_MODELS["primary"],
    "claude-opus-4-20250514": DEFAULT_MODELS["primary"],
    "claude-opus-4-1-20250805": DEFAULT_MODELS["primary"],
    "claude-sonnet-4-6": DEFAULT_MODELS["figure"],
    "claude-sonnet-4-5-20250929": DEFAULT_MODELS["figure"],
    "gpt-5.2": DEFAULT_MODELS["auditor"],
    "gpt-5.2-thinking": DEFAULT_MODELS["auditor"],
    "gpt-5.2-2025-12-11": DEFAULT_MODELS["auditor"],
    "gemini-3-pro": DEFAULT_MODELS["gapHunter"],
    "gemini-3-pro-preview": DEFAULT_MODELS["gapHunter"],
}

_OPENAI_EXCLUDED_TERMS = (
    "audio",
    "chat",
    "codex",
    "embedding",
    "image",
    "mini",
    "moderation",
    "nano",
    "pro",
    "realtime",
    "search",
    "tts",
    "transcribe",
    "translate",
    "video",
    "vision",
)

_GEMINI_EXCLUDED_TERMS = (
    "audio",
    "deep-research",
    "embedding",
    "flash",
    "image",
    "imagen",
    "lite",
    "live",
    "tts",
    "veo",
)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_reason(exc: Exception) -> str:
    return str(exc).replace("\n", " ")[:220]


def _key(keys: Mapping[str, str], *names: str) -> str:
    for name in names:
        value = keys.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _version_tuple(text: str) -> tuple[int, ...]:
    match = re.search(r"(\d+(?:\.\d+)*)", text)
    if not match:
        return (0,)
    return tuple(int(part) for part in match.group(1).split("."))


def _simple_model_id(model_id: str, prefix: str) -> bool:
    return bool(re.fullmatch(rf"{re.escape(prefix)}\d+(?:\.\d+)?", model_id))


def _clean_gemini_name(model: Mapping[str, Any]) -> str:
    value = str(model.get("baseModelId") or model.get("name") or "")
    if value.startswith("models/"):
        value = value.split("/", 1)[1]
    return value.strip()


def _anthropic_family_rank(model_id: str) -> int:
    lowered = model_id.lower()
    if "mythos" in lowered:
        return 4
    if "opus" in lowered:
        return 3
    if "sonnet" in lowered:
        return 2
    if "haiku" in lowered:
        return 1
    return 0


def _select_anthropic_frontier(models: Sequence[Mapping[str, Any]]) -> Optional[str]:
    candidates = []
    for model in models:
        model_id = str(model.get("id") or "").strip()
        if model_id.lower().startswith("claude-"):
            candidates.append(model)

    if not candidates:
        return None

    def sort_key(model: Mapping[str, Any]) -> tuple[int, tuple[int, ...], str]:
        model_id = str(model.get("id") or "").strip()
        created_at = str(model.get("created_at") or "")
        return (_anthropic_family_rank(model_id), _version_tuple(model_id), created_at)

    return str(max(candidates, key=sort_key).get("id") or "").strip() or None


def _select_openai_frontier(models: Sequence[Mapping[str, Any]]) -> Optional[str]:
    candidates = []
    for model in models:
        model_id = str(model.get("id") or "").strip()
        lowered = model_id.lower()
        if not lowered.startswith("gpt-"):
            continue
        if any(term in lowered for term in _OPENAI_EXCLUDED_TERMS):
            continue
        if not re.match(r"^gpt-\d", lowered):
            continue
        candidates.append(model)

    if not candidates:
        return None

    def sort_key(model: Mapping[str, Any]) -> tuple[tuple[int, ...], int, int]:
        model_id = str(model.get("id") or "").lower()
        return (
            _version_tuple(model_id),
            1 if _simple_model_id(model_id, "gpt-") else 0,
            int(model.get("created") or 0),
        )

    return str(max(candidates, key=sort_key).get("id") or "").strip() or None


def _select_gemini_pro(models: Sequence[Mapping[str, Any]]) -> Optional[str]:
    candidates = []
    for model in models:
        model_id = _clean_gemini_name(model)
        lowered = model_id.lower()
        methods = model.get("supportedGenerationMethods") or []
        if methods and "generateContent" not in methods:
            continue
        if not lowered.startswith("gemini-") or "-pro" not in lowered:
            continue
        if any(term in lowered for term in _GEMINI_EXCLUDED_TERMS):
            continue
        candidates.append(model)

    if not candidates:
        return None

    def sort_key(model: Mapping[str, Any]) -> tuple[tuple[int, ...], int]:
        model_id = _clean_gemini_name(model).lower()
        return (_version_tuple(model_id), 1 if "preview" not in model_id else 0)

    return _clean_gemini_name(max(candidates, key=sort_key)) or None


def _fallback_resolution(provider: str, model: str, status: str, reason: str) -> Dict[str, Any]:
    return {
        "provider": provider,
        "model": model,
        "status": status,
        "reason": reason,
        "source": "verified_fallback",
    }


def resolve_latest_model_defaults(
    keys: Mapping[str, str] | None = None,
    timeout_sec: float = 8.0,
) -> Dict[str, Any]:
    """Resolve newest provider models when keys are present, with verified fallbacks."""
    keys = keys or {}
    models = dict(DEFAULT_MODELS)
    resolution: Dict[str, Dict[str, Any]] = {
        "primary": _fallback_resolution("anthropic", models["primary"], "missing_key", "Anthropic key not provided."),
        "figure": _fallback_resolution("anthropic", models["figure"], "missing_key", "Anthropic key not provided."),
        "auditor": _fallback_resolution("openai", models["auditor"], "missing_key", "OpenAI key not provided."),
        "gapHunter": _fallback_resolution("google", models["gapHunter"], "missing_key", "Google Gemini key not provided."),
    }

    anthropic_key = _key(keys, "anthropic", "ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            response = requests.get(
                PROVIDER_MODEL_API_URLS["anthropic"],
                headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01"},
                params={"limit": 1000},
                timeout=timeout_sec,
            )
            response.raise_for_status()
            available = response.json().get("data") or []
            primary = _select_anthropic_frontier(available)
            figure = primary
            if primary:
                models["primary"] = primary
                resolution["primary"] = {
                    "provider": "anthropic",
                    "model": primary,
                    "status": "resolved",
                    "source": PROVIDER_MODEL_API_URLS["anthropic"],
                    "selection": "highest-ranked available Claude frontier model",
                }
            else:
                resolution["primary"] = _fallback_resolution("anthropic", models["primary"], "fallback", "No Claude frontier model found in provider response.")
            if figure:
                models["figure"] = figure
                resolution["figure"] = {
                    "provider": "anthropic",
                    "model": figure,
                    "status": "resolved",
                    "source": PROVIDER_MODEL_API_URLS["anthropic"],
                    "selection": "same Anthropic frontier model as primary extraction",
                }
            else:
                resolution["figure"] = _fallback_resolution("anthropic", models["figure"], "fallback", "No Claude frontier model found in provider response.")
        except requests.RequestException as exc:
            reason = _safe_reason(exc)
            resolution["primary"] = _fallback_resolution("anthropic", models["primary"], "fallback", reason)
            resolution["figure"] = _fallback_resolution("anthropic", models["figure"], "fallback", reason)

    openai_key = _key(keys, "openai", "OPENAI_API_KEY")
    if openai_key:
        try:
            response = requests.get(
                PROVIDER_MODEL_API_URLS["openai"],
                headers={"Authorization": f"Bearer {openai_key}"},
                timeout=timeout_sec,
            )
            response.raise_for_status()
            selected = _select_openai_frontier(response.json().get("data") or [])
            if selected:
                models["auditor"] = selected
                resolution["auditor"] = {
                    "provider": "openai",
                    "model": selected,
                    "status": "resolved",
                    "source": PROVIDER_MODEL_API_URLS["openai"],
                    "selection": "highest base gpt-* frontier version, excluding specialized/pro/mini/nano variants",
                }
            else:
                resolution["auditor"] = _fallback_resolution("openai", models["auditor"], "fallback", "No base GPT frontier model found in provider response.")
        except requests.RequestException as exc:
            resolution["auditor"] = _fallback_resolution("openai", models["auditor"], "fallback", _safe_reason(exc))

    gemini_key = _key(keys, "gemini", "google", "GOOGLE_API_KEY", "GEMINI_API_KEY")
    if gemini_key:
        try:
            response = requests.get(
                PROVIDER_MODEL_API_URLS["google"],
                headers={"x-goog-api-key": gemini_key},
                params={"pageSize": 1000},
                timeout=timeout_sec,
            )
            response.raise_for_status()
            selected = _select_gemini_pro(response.json().get("models") or [])
            if selected:
                models["gapHunter"] = selected
                resolution["gapHunter"] = {
                    "provider": "google",
                    "model": selected,
                    "status": "resolved",
                    "source": PROVIDER_MODEL_API_URLS["google"],
                    "selection": "highest Gemini Pro generateContent model",
                }
            else:
                resolution["gapHunter"] = _fallback_resolution("google", models["gapHunter"], "fallback", "No Gemini Pro generateContent model found in provider response.")
        except requests.RequestException as exc:
            resolution["gapHunter"] = _fallback_resolution("google", models["gapHunter"], "fallback", _safe_reason(exc))

    return {
        "models": models,
        "legacy_model_aliases": LEGACY_MODEL_ALIASES,
        "model_defaults_last_verified": MODEL_DEFAULTS_LAST_VERIFIED,
        "model_default_source_urls": MODEL_DEFAULT_SOURCE_URLS,
        "provider_model_api_urls": PROVIDER_MODEL_API_URLS,
        "model_default_mode": MODEL_DEFAULT_MODE,
        "resolved_at": _utc_iso(),
        "resolution": resolution,
    }


def normalize_model_id(model_id: str) -> str:
    """Return the configured model id, upgrading known retired ids."""
    value = (model_id or "").strip()
    if not value:
        return value
    return LEGACY_MODEL_ALIASES.get(value, value)


def normalize_models(
    models: Mapping[str, str] | None,
    defaults: Mapping[str, str] | None = None,
) -> Dict[str, str]:
    """Apply defaults and legacy aliases to the model bundle sent by the UI."""
    provided = dict(models or {})
    default_bundle = dict(defaults or DEFAULT_MODELS)
    normalized = dict(default_bundle)

    for key in DEFAULT_MODELS:
        value = provided.get(key)
        if value:
            normalized[key] = normalize_model_id(value)

    return normalized


def resolve_models_for_run(
    models: Mapping[str, str] | None,
    keys: Mapping[str, str] | None,
    options: Mapping[str, Any] | None,
) -> tuple[Dict[str, str], Dict[str, Any] | None]:
    """Resolve provider-latest defaults unless the run asks for exact visible IDs."""
    requested = dict(models or {})
    use_latest = True if options is None else bool(options.get("resolve_latest_models", True))
    if not use_latest:
        return normalize_models(requested), None

    default_payload = resolve_latest_model_defaults(keys or {})
    latest_defaults = default_payload.get("models") or DEFAULT_MODELS
    return normalize_models({}, defaults=latest_defaults), default_payload
