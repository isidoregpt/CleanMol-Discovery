"""Optional Chemprop v2 integration scaffolding."""
from __future__ import annotations

from typing import Any, Dict

from .status import get_integration_status


def chemprop_status(options: dict | None = None) -> Dict[str, Any]:
    """Return the Chemprop-specific status row."""
    return get_integration_status({}, options or {}).get("chemprop_v2", {})


def score_with_chemprop_if_available(*_: Any, **__: Any) -> Dict[str, Any]:
    """Placeholder for optional advanced-pack Chemprop inference.

    CleanMol Core deliberately does not depend on Chemprop. The discovery
    workflow catches this status and continues with Morgan baseline scoring.
    """
    return {
        "chemprop_prediction_status": "not_used_scaffolded_integration",
        "chemprop_score_provenance": "chemprop_v2_scaffold_not_active",
        "warning": "Chemprop scoring failed or was unavailable. This run used RDKit Morgan fingerprint baseline and heuristic scoring instead.",
    }
