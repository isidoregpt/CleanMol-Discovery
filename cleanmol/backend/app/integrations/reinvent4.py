"""Optional REINVENT 4 integration scaffolding."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, Iterable


def detect_reinvent4(config_path: str = "") -> Dict[str, Any]:
    executable = shutil.which("reinvent")
    config_exists = bool(config_path and Path(config_path).exists())
    if not executable:
        return {
            "status": "not_installed",
            "message": "REINVENT 4 is optional and not installed. CleanMol will use the built-in rule-based hypothesis generator.",
            "executable": "",
            "config_path": config_path,
        }
    if not config_exists:
        return {
            "status": "installed_but_not_configured",
            "message": "REINVENT 4 is installed but config is missing.",
            "executable": executable,
            "config_path": config_path,
        }
    return {
        "status": "ready",
        "message": "REINVENT 4 is ready for optional candidate generation.",
        "executable": executable,
        "config_path": config_path,
    }


def write_seed_file(path: Path, seeds: Iterable[Dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for idx, seed in enumerate(seeds, start=1):
            smiles = str(seed.get("smiles") or "").strip()
            if smiles:
                handle.write(f"{smiles}\t{seed.get('molecule_id') or f'seed_{idx}'}\n")
    return path
