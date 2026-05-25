"""RDKit Morgan fingerprint nearest-neighbor baseline for CleanMol Core."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from rdkit import Chem, DataStructs
    from rdkit.Chem import rdMolDescriptors
except ImportError:  # pragma: no cover - handled by status checks
    Chem = None
    DataStructs = None
    rdMolDescriptors = None


@dataclass
class MorganReference:
    name: str
    smiles: str
    source: str
    activity_label: str
    endpoint: str
    value: str
    units: str
    score: float
    fingerprint: Any


@dataclass
class MorganBaseline:
    references: List[MorganReference]
    status: str
    message: str


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _safe_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    import re

    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def fingerprint_smiles(smiles: str, radius: int = 2, n_bits: int = 2048) -> Tuple[Optional[Any], Optional[str]]:
    """Validate a SMILES string and return a Morgan fingerprint."""
    if not smiles:
        return None, "missing_smiles"
    if Chem is None or rdMolDescriptors is None:
        return None, "rdkit_unavailable"
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None, "invalid_smiles"
    fp = rdMolDescriptors.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
    return fp, None


def _activity_score(row: Dict[str, Any]) -> Optional[float]:
    label = _text(row.get("activity_label")).lower()
    value = _safe_float(row.get("value"))
    if label in {"active", "hit", "positive"}:
        return 85.0
    if label in {"inactive", "negative", "not_active"}:
        return 20.0
    if value is not None and value > 0:
        # Lower MIC-like values are better. This is a baseline prior, not a calibrated model.
        return max(0.0, min(100.0, 100.0 - 22.0 * math.log10(value + 1.0)))
    return None


def build_morgan_baseline(activity_rows: Iterable[Dict[str, Any]]) -> MorganBaseline:
    """Build a nearest-neighbor baseline from activity/reference rows."""
    references: List[MorganReference] = []
    if Chem is None:
        return MorganBaseline([], "rdkit_unavailable", "RDKit is not available.")

    for row in activity_rows:
        smiles = _text(row.get("smiles"))
        score = _activity_score(row)
        if not smiles or score is None:
            continue
        fingerprint, error = fingerprint_smiles(smiles)
        if error or fingerprint is None:
            continue
        references.append(
            MorganReference(
                name=_text(row.get("molecule_name") or row.get("name") or row.get("compound_name")),
                smiles=smiles,
                source=_text(row.get("source") or row.get("provenance")),
                activity_label=_text(row.get("activity_label")),
                endpoint=_text(row.get("endpoint") or row.get("assay_type")),
                value=_text(row.get("value")),
                units=_text(row.get("units")),
                score=float(score),
                fingerprint=fingerprint,
            )
        )

    status = "ready" if references else "empty"
    message = (
        f"Built Morgan baseline with {len(references)} reference rows."
        if references
        else "No usable Morgan baseline references were available."
    )
    return MorganBaseline(references, status, message)


def score_candidate_against_baseline(
    smiles: str,
    baseline: Optional[MorganBaseline],
    *,
    min_similarity: float = 0.2,
    max_neighbors: int = 7,
) -> Dict[str, Any]:
    """Score a candidate against the nearest Morgan fingerprint references."""
    empty = {
        "nearest_reference_name": "",
        "nearest_reference_smiles": "",
        "nearest_reference_similarity": 0.0,
        "nearest_reference_source": "",
        "nearest_reference_activity_label": "",
        "nearest_reference_endpoint": "",
        "nearest_reference_value": "",
        "nearest_reference_units": "",
        "morgan_baseline_score": None,
        "morgan_neighbor_count": 0,
        "morgan_score_provenance": "heuristic_prior_no_reference_neighbors_available",
    }
    if not baseline or not baseline.references:
        return dict(empty)

    fingerprint, error = fingerprint_smiles(smiles)
    if error or fingerprint is None or DataStructs is None:
        result = dict(empty)
        result["morgan_score_provenance"] = f"heuristic_prior_morgan_unavailable_{error or 'unknown'}"
        return result

    scored: List[Tuple[float, MorganReference]] = []
    for ref in baseline.references:
        similarity = float(DataStructs.TanimotoSimilarity(fingerprint, ref.fingerprint))
        if similarity >= min_similarity:
            scored.append((similarity, ref))
    scored.sort(key=lambda item: item[0], reverse=True)
    top = scored[:max_neighbors]
    if not top:
        return dict(empty)

    total_weight = sum(similarity for similarity, _ in top)
    baseline_score = sum(similarity * ref.score for similarity, ref in top) / total_weight if total_weight else 0
    nearest_similarity, nearest_ref = top[0]
    return {
        "nearest_reference_name": nearest_ref.name,
        "nearest_reference_smiles": nearest_ref.smiles,
        "nearest_reference_similarity": round(nearest_similarity, 4),
        "nearest_reference_source": nearest_ref.source,
        "nearest_reference_activity_label": nearest_ref.activity_label,
        "nearest_reference_endpoint": nearest_ref.endpoint,
        "nearest_reference_value": nearest_ref.value,
        "nearest_reference_units": nearest_ref.units,
        "morgan_baseline_score": round(float(baseline_score), 2),
        "morgan_neighbor_count": len(top),
        "morgan_score_provenance": "rdkit_morgan_fingerprint_baseline_plus_discovery_profile",
    }
