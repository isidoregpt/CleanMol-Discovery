"""Unified integration status detection for CleanMol Discovery."""
from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional


def _key(keys: Optional[Dict[str, str]], *names: str) -> str:
    keys = keys or {}
    for name in names:
        value = keys.get(name) or os.environ.get(name)
        if value:
            return str(value).strip()
    return ""


def _disabled(options: Optional[Dict[str, Any]], integration_id: str) -> bool:
    options = options or {}
    disabled = options.get("disabled_integrations") or []
    if isinstance(disabled, str):
        disabled = [item.strip() for item in disabled.split(",")]
    return integration_id in set(disabled)


def _version(package: str) -> Optional[str]:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def _row(
    status: str,
    message: str,
    *,
    required: bool = False,
    enabled: bool = True,
    version: Optional[str] = None,
    detail: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    item: Dict[str, Any] = {
        "status": status,
        "required": required,
        "enabled": enabled,
        "message": message,
    }
    if version:
        item["version"] = version
    if detail:
        item["detail"] = detail
    return item


def get_integration_status(keys: dict | None = None, options: dict | None = None) -> dict:
    """Return non-technical status rows for core and optional integrations."""
    options = options or {}
    reduced_egress = bool(options.get("reduced_egress") or options.get("local_only"))
    statuses: Dict[str, Any] = {}

    statuses["cleanmol_core"] = _row(
        "ready",
        "CleanMol Core is available.",
        required=True,
        enabled=True,
    )

    rdkit_version = _version("rdkit")
    if importlib.util.find_spec("rdkit") and rdkit_version:
        statuses["rdkit"] = _row(
            "ready",
            "RDKit is available for SMILES validation, molecular properties, and fingerprints.",
            required=True,
            enabled=True,
            version=rdkit_version,
        )
        statuses["morgan_baseline"] = _row(
            "ready",
            "Morgan fingerprint baseline is available as the default chemically informed similarity baseline.",
            required=True,
            enabled=True,
        )
    else:
        statuses["rdkit"] = _row(
            "error",
            "RDKit is required for CleanMol Core but was not detected.",
            required=True,
            enabled=False,
        )
        statuses["morgan_baseline"] = _row(
            "error",
            "Morgan fingerprint baseline requires RDKit.",
            required=True,
            enabled=False,
        )

    chemprop_disabled = _disabled(options, "chemprop_v2")
    chemprop_version = _version("chemprop")
    if chemprop_disabled:
        statuses["chemprop_v2"] = _row(
            "disabled",
            "Chemprop v2 is disabled. CleanMol uses the RDKit Morgan baseline and heuristic triage scoring.",
            required=False,
            enabled=False,
        )
    elif chemprop_version:
        statuses["chemprop_v2"] = _row(
            "optional",
            "Chemprop v2 is detected, but CleanMol's Chemprop scoring integration is scaffolded and not active in this public preview.",
            required=False,
            enabled=False,
            version=chemprop_version,
        )
    else:
        statuses["chemprop_v2"] = _row(
            "optional",
            "Chemprop v2 support is scaffolded but not active scoring in this public preview. CleanMol uses RDKit Morgan baseline and heuristic scoring.",
            required=False,
            enabled=False,
        )

    reinvent_disabled = _disabled(options, "reinvent4")
    reinvent_path = shutil.which("reinvent")
    reinvent_config = options.get("reinvent_config_path") or os.environ.get("CLEANMOL_REINVENT_CONFIG", "")
    reinvent_config_exists = bool(reinvent_config and Path(str(reinvent_config)).exists())
    if reinvent_disabled:
        statuses["reinvent4"] = _row(
            "disabled",
            "REINVENT 4 is disabled. CleanMol will use the built-in hypothesis generator.",
            required=False,
            enabled=False,
        )
    elif not reinvent_path:
        statuses["reinvent4"] = _row(
            "not_installed",
            "REINVENT 4 is optional and not installed. CleanMol will use the built-in rule-based hypothesis generator.",
            required=False,
            enabled=False,
        )
    elif not reinvent_config_exists:
        statuses["reinvent4"] = _row(
            "installed_but_not_configured",
            "REINVENT 4 is installed but no config file is selected.",
            required=False,
            enabled=False,
            detail={"executable": reinvent_path, "config_path": reinvent_config or ""},
        )
    else:
        statuses["reinvent4"] = _row(
            "ready",
            "REINVENT 4 is ready for optional candidate generation.",
            required=False,
            enabled=True,
            detail={"executable": reinvent_path, "config_path": reinvent_config},
        )

    fairchem_disabled = _disabled(options, "fairchem_uma")
    fairchem_version = _version("fairchem-core") or _version("fairchem")
    if fairchem_disabled:
        statuses["fairchem_uma"] = _row(
            "disabled",
            "FairChem/UMA is disabled. CleanMol can still prepare UMA review files.",
            required=False,
            enabled=False,
        )
    elif not importlib.util.find_spec("fairchem"):
        statuses["fairchem_uma"] = _row(
            "not_installed",
            "FairChem/UMA is optional and not installed. CleanMol prepares handoff files but does not run UMA by default.",
            required=False,
            enabled=False,
        )
    else:
        statuses["fairchem_uma"] = _row(
            "expert_manual",
            "FairChem/UMA is available as an expert/manual atomistic review path, not an antimicrobial predictor.",
            required=False,
            enabled=False,
            version=fairchem_version,
        )

    provider_rows = [
        ("anthropic_api", "Anthropic API", _key(keys, "anthropic", "ANTHROPIC_API_KEY")),
        ("openai_api", "OpenAI API", _key(keys, "openai", "OPENAI_API_KEY")),
        ("google_gemini_api", "Google Gemini API", _key(keys, "gemini", "google", "GOOGLE_API_KEY", "GEMINI_API_KEY")),
        ("huggingface_api", "Hugging Face API", _key(keys, "hf", "huggingface", "HF_TOKEN")),
    ]
    for integration_id, label, value in provider_rows:
        if reduced_egress:
            statuses[integration_id] = _row(
                "disabled",
                f"{label} calls are disabled by reduced-egress / local-only mode.",
                required=False,
                enabled=False,
            )
            continue
        statuses[integration_id] = _row(
            "ready" if value else "api_key_missing",
            f"{label} key {'is present' if value else 'is missing'}.",
            required=integration_id == "anthropic_api",
            enabled=bool(value),
        )

    return statuses
