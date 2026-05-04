"""
Dataset Quality Equalizer for CleanMol Discovery.

The same gates are applied to uploaded, online-pulled, and auto-created data.
This keeps a no-resource user's dataset from being treated as curated-grade
until it meets comparable evidence, diversity, and provenance standards.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Set


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _lower(value: Any) -> str:
    return _text(value).lower()


def _unique_smiles(rows: Iterable[Dict[str, Any]]) -> Set[str]:
    return {_text(row.get("smiles")) for row in rows if _text(row.get("smiles"))}


def _source_set(rows: Iterable[Dict[str, Any]], manifests: List[Dict[str, Any]]) -> Set[str]:
    sources = {_text(row.get("source")) for row in rows if _text(row.get("source"))}
    for item in manifests:
        source = item.get("dataset") or item.get("source") or item.get("path")
        if source:
            sources.add(_text(source))
    return sources


def _organism_group(value: Any) -> str:
    text = _lower(value)
    if not text:
        return ""
    if any(term in text for term in ("aureus", "staphylococcus", "gram-positive", "gram positive")):
        return "gram_positive"
    if any(term in text for term in ("coli", "escherichia", "pseudomonas", "aeruginosa", "gram-negative", "gram negative")):
        return "gram_negative"
    if any(term in text for term in ("candida", "albicans", "fung", "yeast")):
        return "fungal"
    if any(term in text for term in ("biofilm", "surface")):
        return "biofilm_or_surface"
    return "other_named"


def _scaffold_key_from_smiles(smiles: str) -> str:
    smiles = _text(smiles)
    if not smiles:
        return ""
    if "[P+]" in smiles:
        return "phosphonium"
    if "[n+]" in smiles or "[nH+]" in smiles:
        return "aromatic_heterocycle_cation"
    if smiles.count("[N+]") >= 2:
        return "gemini_or_bis_qac"
    if "[N+]" in smiles and "c1" in smiles:
        return "aromatic_qac"
    if "[N+]" in smiles:
        return "qac"
    if "[S+]" in smiles:
        return "sulfonium"
    return re.sub(r"[^A-Za-z0-9+\\[\\]]", "", smiles[:32])


def _scaffold_diversity(rows: Iterable[Dict[str, Any]]) -> int:
    keys = set()
    for row in rows:
        tags = row.get("modern_scaffold_tags")
        if isinstance(tags, list) and tags:
            keys.add("|".join(sorted(str(tag) for tag in tags[:3])))
            continue
        family = _text(row.get("family"))
        if family:
            keys.add(family)
            continue
        key = _scaffold_key_from_smiles(_text(row.get("smiles")))
        if key:
            keys.add(key)
    return len(keys)


def _synthetic_fraction(rows: Iterable[Dict[str, Any]]) -> float:
    total = 0
    synthetic = 0
    for row in rows:
        total += 1
        provenance = _lower(row.get("provenance") or row.get("generation_provenance") or row.get("score_provenance"))
        source = _lower(row.get("source"))
        if "synthetic" in provenance or "prior" in provenance or "starter_prior" in source or "cleanmol_builtin" in provenance:
            synthetic += 1
    if total == 0:
        return 1.0
    return synthetic / total


def _modern_source_count(manifests: List[Dict[str, Any]]) -> int:
    count = 0
    for item in manifests:
        modernity = _lower(item.get("modernity"))
        source = _lower(item.get("dataset") or item.get("source"))
        status = _lower(item.get("status"))
        if status in {"error", "missing", "not_pulled"}:
            continue
        if any(term in modernity for term in ("modern", "current", "maintained")):
            count += 1
        elif any(term in source for term in ("chembl", "tox21", "stokes", "chaff", "cleanmol_analysis_ready")):
            count += 1
    return count


def _gate(name: str, score: float, passed: bool, value: Any, target: str, recommendation: str) -> Dict[str, Any]:
    return {
        "name": name,
        "score": round(max(0, min(100, score)), 2),
        "passed": bool(passed),
        "value": value,
        "target": target,
        "recommendation": recommendation,
    }


def assess_dataset_quality(
    activity_rows: List[Dict[str, Any]],
    toxicity_rows: List[Dict[str, Any]],
    seeds: List[Dict[str, Any]],
    ranked_rows: List[Dict[str, Any]],
    manifests: List[Dict[str, Any]],
) -> Dict[str, Any]:
    activity_smiles = _unique_smiles(activity_rows)
    toxicity_smiles = _unique_smiles(toxicity_rows)
    seed_smiles = _unique_smiles(seeds)
    candidate_smiles = _unique_smiles(ranked_rows)
    sources = _source_set([*activity_rows, *toxicity_rows], manifests)
    organism_groups = {
        group
        for group in (_organism_group(row.get("organism")) for row in activity_rows)
        if group
    }

    activity_label_count = sum(1 for row in activity_rows if _text(row.get("activity_label")) or _text(row.get("value")))
    toxicity_label_count = sum(1 for row in toxicity_rows if _text(row.get("toxicity_value")) or _text(row.get("toxicity_label")))
    candidate_modern_count = sum(1 for row in ranked_rows if row.get("candidate_tier") == "modern_seed")
    top_candidate_count = min(20, len(ranked_rows))
    top_modern_count = sum(1 for row in ranked_rows[:top_candidate_count] if row.get("candidate_tier") == "modern_seed")
    candidate_modern_fraction = top_modern_count / top_candidate_count if top_candidate_count else 0

    source_diversity = len(sources)
    modern_sources = _modern_source_count(manifests)
    scaffold_diversity = max(_scaffold_diversity(seeds), _scaffold_diversity(ranked_rows))
    synthetic_fraction = max(_synthetic_fraction(activity_rows), _synthetic_fraction(ranked_rows))

    gates = [
        _gate(
            "activity_evidence_depth",
            min(100, len(activity_smiles) / 250 * 100),
            len(activity_smiles) >= 250,
            len(activity_smiles),
            ">=250 unique activity molecules for curated-grade; >=50 for useful starter",
            "Pull ChEMBL/PubChem/HF activity sources or add more CleanMol-extracted papers.",
        ),
        _gate(
            "toxicity_selectivity_depth",
            min(100, len(toxicity_smiles) / 150 * 100),
            len(toxicity_smiles) >= 150,
            len(toxicity_smiles),
            ">=150 unique toxicity/selectivity molecules",
            "Enable Tox21/ToxCast/ChAFF-style sources or upload hemolysis/cytotoxicity data.",
        ),
        _gate(
            "label_density",
            min(100, (activity_label_count + toxicity_label_count) / 250 * 100),
            activity_label_count >= 100 and toxicity_label_count >= 50,
            {"activity_labels": activity_label_count, "toxicity_labels": toxicity_label_count},
            ">=100 activity labels and >=50 toxicity/selectivity labels",
            "Prefer measured endpoints over unlabeled SMILES-only corpora.",
        ),
        _gate(
            "source_diversity",
            min(100, source_diversity / 4 * 100),
            source_diversity >= 4,
            source_diversity,
            ">=4 independent sources",
            "Combine uploaded data, CleanMol literature extraction, ChEMBL/PubChem, and HF safety sources.",
        ),
        _gate(
            "modern_source_presence",
            min(100, modern_sources / 3 * 100),
            modern_sources >= 3,
            modern_sources,
            ">=3 modern/current/maintained sources",
            "Use the Source Library and avoid relying on one old benchmark.",
        ),
        _gate(
            "organism_or_assay_breadth",
            min(100, len(organism_groups) / 3 * 100),
            len(organism_groups) >= 3,
            sorted(organism_groups),
            ">=3 organism/assay groups, ideally Gram-positive, Gram-negative, fungal/biofilm",
            "Add papers or assays spanning multiple organisms and surface/formulation conditions.",
        ),
        _gate(
            "modern_seed_depth",
            min(100, len(seed_smiles) / 30 * 100),
            len(seed_smiles) >= 30,
            len(seed_smiles),
            ">=30 modern generation seeds",
            "Extract more QAC/biocide papers or pull modern cationic/amphiphilic source data.",
        ),
        _gate(
            "scaffold_diversity",
            min(100, scaffold_diversity / 8 * 100),
            scaffold_diversity >= 8,
            scaffold_diversity,
            ">=8 scaffold families",
            "Avoid a one-family QAC-only dataset; include phosphonium, pyridinium, imidazolium, gemini/bis variants, and safety negatives.",
        ),
        _gate(
            "synthetic_prior_separation",
            max(0, 100 - synthetic_fraction * 100),
            synthetic_fraction <= 0.35,
            round(synthetic_fraction, 3),
            "<=35% synthetic/model-prior dominance in training/review packet",
            "Keep synthetic priors separate and add measured/public experimental rows before calling the dataset curated-grade.",
        ),
        _gate(
            "candidate_quality",
            candidate_modern_fraction * 100,
            candidate_modern_fraction >= 0.8 and len(candidate_smiles) >= 20,
            {"top_modern_fraction": round(candidate_modern_fraction, 3), "ranked_candidates": len(candidate_smiles)},
            ">=80% of top 20 candidates modern_seed and >=20 ranked candidates",
            "Tighten generation filters or increase modern seed diversity.",
        ),
    ]

    weighted_score = round(sum(gate["score"] for gate in gates) / len(gates), 2)
    hard_failures = [gate for gate in gates if not gate["passed"]]

    if weighted_score >= 82 and len(hard_failures) <= 2 and synthetic_fraction <= 0.35:
        status = "curated_grade"
        status_label = "Curated-Grade"
    elif weighted_score >= 65:
        status = "strong_starter"
        status_label = "Strong Starter"
    elif weighted_score >= 45:
        status = "useful_starter"
        status_label = "Useful Starter"
    else:
        status = "not_ready"
        status_label = "Not Ready"

    return {
        "status": status,
        "status_label": status_label,
        "quality_score": weighted_score,
        "gates_passed": sum(1 for gate in gates if gate["passed"]),
        "gates_total": len(gates),
        "hard_failures": [gate["name"] for gate in hard_failures],
        "gates": gates,
        "metrics": {
            "unique_activity_molecules": len(activity_smiles),
            "unique_toxicity_molecules": len(toxicity_smiles),
            "unique_seed_molecules": len(seed_smiles),
            "unique_ranked_candidates": len(candidate_smiles),
            "source_diversity": source_diversity,
            "modern_source_count": modern_sources,
            "organism_groups": sorted(organism_groups),
            "scaffold_diversity": scaffold_diversity,
            "synthetic_fraction": round(synthetic_fraction, 3),
            "top_candidate_modern_fraction": round(candidate_modern_fraction, 3),
        },
        "recommendations": [
            gate["recommendation"]
            for gate in hard_failures[:6]
        ],
        "equalizer_note": (
            "The same quality gates are applied to uploaded and auto-created datasets. "
            "Synthetic/model-prior rows can help start discovery but cannot by themselves make a dataset curated-grade."
        ),
    }
