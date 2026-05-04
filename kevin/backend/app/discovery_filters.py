"""
Modern disinfectant discovery filters.

These heuristics do not declare a molecule safe, effective, or synthesizable.
They only decide whether an extracted molecule is a useful seed for the
Lysol 2.0 discovery loop, or whether it belongs in the baseline/negative pool.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List


MODERN_SEED_RECOMMENDATION = "use_as_generation_seed"
REVIEW_RECOMMENDATION = "review_before_seed"
BASELINE_RECOMMENDATION = "use_only_as_negative_or_baseline"
EXCLUDE_RECOMMENDATION = "exclude_until_structure_confirmed"


MODERN_HEAD_GROUP_KEYWORDS = {
    "quaternary_ammonium",
    "quaternary_phosphonium",
    "phosphonium",
    "imidazolium",
    "pyridinium",
    "guanidinium",
    "sulfonium",
    "bis_quaternary_ammonium",
    "gemini_quaternary_ammonium",
    "bis_cationic",
    "zwitterionic_amphiphile",
}


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _lower_join(values: Iterable[Any]) -> str:
    return " ".join(_as_text(value).lower() for value in values if value is not None)


def _numeric_values(value: Any) -> List[float]:
    """Extract numeric values from list-like fields or loose text."""
    if value is None:
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, (list, tuple, set)):
        numbers: List[float] = []
        for item in value:
            numbers.extend(_numeric_values(item))
        return numbers
    text = _as_text(value)
    return [float(match) for match in re.findall(r"\d+(?:\.\d+)?", text)]


def _count_positive_centers(smiles: str) -> int:
    return len(re.findall(r"\[[A-Za-z][^\]]*\+\]", smiles))


def _count_atom_symbol(smiles: str, symbol: str) -> int:
    if symbol == "N":
        return smiles.count("N") + smiles.count("n")
    if symbol == "C":
        return smiles.count("C") + smiles.count("c")
    return smiles.count(symbol)


def _long_alkyl_tail_count(smiles: str, molecule: Dict[str, Any]) -> int:
    lengths = []
    for field in ("chain_lengths", "tail_lengths", "alkyl_chain_lengths"):
        lengths.extend(_numeric_values(molecule.get(field)))

    model_tail_count = sum(1 for length in lengths if length >= 8)
    linear_tail_count = len(re.findall(r"C{8,}", smiles))
    return max(model_tail_count, linear_tail_count)


def _has_negative_group(smiles: str) -> bool:
    return any(
        marker in smiles
        for marker in ("[O-]", "C(=O)[O-]", "S(=O)(=O)[O-]", "P(=O)([O-])")
    )


def _infer_tags(smiles: str, molecule: Dict[str, Any]) -> List[str]:
    text = _lower_join(
        [
            molecule.get("name_as_written"),
            molecule.get("normalized_name"),
            molecule.get("head_group_class"),
            molecule.get("scaffold_class"),
            molecule.get("generation_notes"),
        ]
    )
    tags = set()

    if re.search(r"\[N\+\]", smiles) or "quaternary ammonium" in text or "alkyl dimethyl benzyl ammonium" in text:
        tags.add("quaternary_ammonium")
    if "[P+]" in smiles or "phosphonium" in text:
        tags.add("quaternary_phosphonium")
    if "[S+]" in smiles or "sulfonium" in text:
        tags.add("sulfonium")
    if re.search(r"\[nH?\+\]", smiles) or "imidazolium" in text:
        tags.add("imidazolium")
    if "pyridinium" in text:
        tags.add("pyridinium")
    if "guanidinium" in text or re.search(r"C\(=N\)N", smiles):
        tags.add("guanidinium")

    cationic_centers = _count_positive_centers(smiles)
    if cationic_centers >= 2 or any(word in text for word in ("gemini", "bis-qac", "bis qac", "bis-quat", "bis quat", "bis-cationic", "bis cationic")):
        tags.add("gemini_or_bis_cationic")

    if ("benzalkonium" in text or "benzethonium" in text or "cetylpyridinium" in text) and tags:
        tags.add("aromatic_cationic_surfactant")
    if ("c1ccccc1" in smiles or "c1cc" in smiles) and tags:
        tags.add("aromatic_cationic_surfactant")

    if _has_negative_group(smiles) and cationic_centers > 0:
        tags.add("zwitterionic_amphiphile")

    if _long_alkyl_tail_count(smiles, molecule) > 0:
        tags.add("lipophilic_tail")

    return sorted(tags)


def _infer_primary_head_group(tags: List[str], existing: Any) -> str:
    existing_text = _as_text(existing).strip()
    if existing_text:
        return existing_text

    priority = [
        "gemini_or_bis_cationic",
        "quaternary_phosphonium",
        "imidazolium",
        "pyridinium",
        "quaternary_ammonium",
        "guanidinium",
        "sulfonium",
        "zwitterionic_amphiphile",
    ]
    for tag in priority:
        if tag in tags:
            return "bis_cationic" if tag == "gemini_or_bis_cationic" else tag
    return ""


def infer_discovery_profile(molecule: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score an extracted molecule as a discovery seed.

    The score is intentionally conservative: modern cationic/amphiphilic
    scaffolds are promoted, while neutral single-nitrogen compounds are kept
    as references unless supported by later model/lab evidence.
    """
    smiles = _as_text(molecule.get("smiles")).strip()
    name_text = _lower_join([molecule.get("name_as_written"), molecule.get("normalized_name")])
    head_group_text = _lower_join([molecule.get("head_group_class"), molecule.get("scaffold_class")])

    if not smiles:
        return {
            "modern_disinfectant_score": 0,
            "candidate_tier": "insufficient_structure",
            "modern_scaffold_tags": [],
            "legacy_flags": ["missing_smiles"],
            "primary_head_group_class": _infer_primary_head_group([], molecule.get("head_group_class")),
            "stable_cationic_center_count": 0,
            "lipophilic_tail_count": 0,
            "generation_recommendation": EXCLUDE_RECOMMENDATION,
            "generation_notes": "No structure available; confirm SMILES before using in any generator.",
        }

    tags = _infer_tags(smiles, molecule)
    positive_centers = _count_positive_centers(smiles)
    nitrogen_count = _count_atom_symbol(smiles, "N")
    carbon_count = _count_atom_symbol(smiles, "C")
    tail_count = _long_alkyl_tail_count(smiles, molecule)
    stable_cationic_tags = [
        tag
        for tag in tags
        if tag
        in {
            "quaternary_ammonium",
            "quaternary_phosphonium",
            "imidazolium",
            "pyridinium",
            "guanidinium",
            "sulfonium",
            "gemini_or_bis_cationic",
            "zwitterionic_amphiphile",
        }
    ]

    score = 0
    legacy_flags = []

    if stable_cationic_tags:
        score += 40
    if positive_centers >= 2 or "gemini_or_bis_cationic" in tags:
        score += 20
    if tail_count > 0:
        score += 20
    elif carbon_count >= 12 and stable_cationic_tags:
        score += 10
    if any(tag in tags for tag in ("imidazolium", "pyridinium", "quaternary_phosphonium", "sulfonium", "guanidinium")):
        score += 10
    if "aromatic_cationic_surfactant" in tags:
        score += 8
    if "zwitterionic_amphiphile" in tags:
        score += 6
    if head_group_text and any(keyword in head_group_text for keyword in MODERN_HEAD_GROUP_KEYWORDS):
        score += 6

    has_neutral_single_n = nitrogen_count == 1 and positive_centers == 0 and not stable_cationic_tags
    has_simple_amine_name = any(word in name_text for word in ("monoamine", "ethylamine", "propylamine", "butylamine", "aniline"))
    has_amine_without_modern_head = "amine" in name_text and not stable_cationic_tags

    if has_neutral_single_n:
        legacy_flags.append("neutral_single_nitrogen")
        score -= 35
    if has_simple_amine_name or has_amine_without_modern_head:
        legacy_flags.append("simple_amine_reference")
        score -= 20
    if positive_centers == 0 and not stable_cationic_tags:
        legacy_flags.append("no_stable_cationic_head_group")
        score -= 20
    if tail_count == 0 and carbon_count < 10 and stable_cationic_tags:
        legacy_flags.append("weak_or_missing_lipophilic_tail")
        score -= 8
    if molecule.get("smiles_valid") is False:
        legacy_flags.append("invalid_smiles")
        score -= 50

    score = max(0, min(100, score))

    if molecule.get("smiles_valid") is False:
        tier = "insufficient_structure"
        recommendation = EXCLUDE_RECOMMENDATION
        notes = "Invalid SMILES; repair the structure before discovery use."
    elif score >= 60 and "neutral_single_nitrogen" not in legacy_flags:
        tier = "modern_seed"
        recommendation = MODERN_SEED_RECOMMENDATION
        notes = "Modern cationic/amphiphilic scaffold suitable as a generation seed after chemist review."
    elif score >= 40 and "no_stable_cationic_head_group" not in legacy_flags:
        tier = "needs_review"
        recommendation = REVIEW_RECOMMENDATION
        notes = "Potentially relevant, but confirm activity evidence, counterion, and formulation context before seeding."
    else:
        tier = "legacy_or_low_priority"
        recommendation = BASELINE_RECOMMENDATION
        notes = "Keep as an activity reference, baseline, or negative example; do not use as a primary generation seed."

    return {
        "modern_disinfectant_score": score,
        "candidate_tier": tier,
        "modern_scaffold_tags": tags,
        "legacy_flags": sorted(set(legacy_flags)),
        "primary_head_group_class": _infer_primary_head_group(tags, molecule.get("head_group_class")),
        "stable_cationic_center_count": positive_centers,
        "lipophilic_tail_count": tail_count,
        "generation_recommendation": recommendation,
        "generation_notes": notes,
    }


def enrich_modern_discovery_fields(molecule: Dict[str, Any]) -> Dict[str, Any]:
    """Attach discovery-profile fields to a molecule dict in place."""
    profile = infer_discovery_profile(molecule)
    for key, value in profile.items():
        if key == "primary_head_group_class":
            continue
        molecule[key] = value

    primary_head = profile.get("primary_head_group_class")
    if primary_head and not molecule.get("head_group_class"):
        molecule["head_group_class"] = primary_head

    if not molecule.get("scaffold_class"):
        tags = profile.get("modern_scaffold_tags") or []
        molecule["scaffold_class"] = tags[0] if tags else ""

    return profile


def is_generation_seed(molecule: Dict[str, Any]) -> bool:
    if molecule.get("generation_recommendation") != MODERN_SEED_RECOMMENDATION:
        return False
    if molecule.get("smiles_valid") is False:
        return False
    return bool(molecule.get("smiles"))


def is_legacy_or_low_priority(molecule: Dict[str, Any]) -> bool:
    return molecule.get("candidate_tier") == "legacy_or_low_priority" or bool(molecule.get("legacy_flags"))
