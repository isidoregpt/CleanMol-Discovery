"""FairChem / UMA handoff helpers."""
from __future__ import annotations

UMA_WARNING = (
    "UMA is an atomistic plausibility and structure-review resource. "
    "It does not prove antimicrobial activity, safety, synthesis feasibility, "
    "regulatory readiness, or commercial suitability."
)


def handoff_message() -> str:
    return "CleanMol prepares a FairChem/UMA review handoff file. It does not run UMA by default."
