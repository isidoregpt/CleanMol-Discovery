"""
Online chemistry source catalog for Discovery mode.

The catalog is written for non-technical chemists: each source has plain-English
fit, recency, provenance, and pull status metadata.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:  # pragma: no cover - backend requirements install requests
    requests = None


CURATED_SOURCE_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "hf:scbirlab/stokes-2020-ai",
        "name": "Stokes 2020 Antibiotic Discovery",
        "connector": "huggingface",
        "dataset_id": "scbirlab/stokes-2020-ai",
        "role": "activity_reference",
        "domain_fit": "antibacterial small-molecule activity reference",
        "modernity": "modern_ml_benchmark",
        "default_selected": True,
        "pull_supported": True,
        "use_guidance": "Good activity reference data, but not disinfectant-specific. Combine with CleanMol QAC literature.",
        "source_url": "https://huggingface.co/datasets/scbirlab/stokes-2020-ai",
    },
    {
        "id": "hf:scikit-fingerprints/MoleculeNet_Tox21",
        "name": "MoleculeNet Tox21",
        "connector": "huggingface",
        "dataset_id": "scikit-fingerprints/MoleculeNet_Tox21",
        "role": "toxicity_selectivity",
        "domain_fit": "toxicity guardrail",
        "modernity": "maintained_benchmark",
        "default_selected": True,
        "pull_supported": True,
        "use_guidance": "Use as safety/selectivity guardrail, not as antimicrobial activity truth.",
        "source_url": "https://huggingface.co/datasets/scikit-fingerprints/MoleculeNet_Tox21",
    },
    {
        "id": "hf:antoinebcx/smiles-molecules-chembl",
        "name": "ChEMBL Molecule Generation SMILES",
        "connector": "huggingface",
        "dataset_id": "antoinebcx/smiles-molecules-chembl",
        "role": "generative_prior",
        "domain_fit": "large bioactive-molecule SMILES prior",
        "modernity": "use_as_prior_not_activity_truth",
        "default_selected": True,
        "pull_supported": True,
        "use_guidance": "Useful for generator diversity. Do not let it overpower disinfectant/QAC-specific data.",
        "source_url": "https://huggingface.co/datasets/antoinebcx/smiles-molecules-chembl",
    },
    {
        "id": "hf:maomlab/ChAFF",
        "name": "ChAFF Assay-Interference Liabilities",
        "connector": "huggingface",
        "dataset_id": "maomlab/ChAFF",
        "role": "liability_filter",
        "domain_fit": "reactivity/artifact/liability flags",
        "modernity": "modern_liability_dataset",
        "default_selected": False,
        "pull_supported": True,
        "use_guidance": "Useful to penalize assay artifacts/reactive liabilities in generated candidates.",
        "source_url": "https://huggingface.co/datasets/maomlab/ChAFF",
    },
    {
        "id": "chembl:antimicrobial-mic",
        "name": "ChEMBL Antimicrobial MIC Rows",
        "connector": "chembl",
        "role": "activity_reference",
        "domain_fit": "curated bioactivity rows with MIC-like endpoints",
        "modernity": "current_database_release",
        "default_selected": True,
        "pull_supported": True,
        "use_guidance": "Good public bioactivity source. CleanMol filters for antimicrobial-looking assay text and MIC/MBC-like endpoints.",
        "source_url": "https://www.ebi.ac.uk/chembl/api/data/activity",
    },
    {
        "id": "pubchem:bioassay-antimicrobial",
        "name": "PubChem BioAssay Antimicrobial Search",
        "connector": "pubchem",
        "role": "activity_reference",
        "domain_fit": "large public bioassay universe",
        "modernity": "current_public_repository",
        "default_selected": False,
        "pull_supported": False,
        "use_guidance": "Cataloged for discovery. CleanMol links this source now; fully automated topical BioAssay pulls need curated AID selection.",
        "source_url": "https://pubchem.ncbi.nlm.nih.gov/docs/bioassays",
    },
    {
        "id": "fairchem:uma-omol",
        "name": "FAIR Chemistry UMA for Molecules",
        "connector": "fairchem",
        "role": "physics_review",
        "domain_fit": "atomistic plausibility review for molecule candidates",
        "modernity": "current_fairchem_v2_optional",
        "default_selected": False,
        "pull_supported": False,
        "use_guidance": (
            "Optional downstream physics layer. CleanMol prepares fairchem_uma_candidates.csv; "
            "install fairchem-core separately and request gated UMA access before running local UMA jobs."
        ),
        "source_url": "https://fair-chem.github.io/install/",
        "docs_url": "https://fair-chem.github.io/quickstart/",
    },
]


def default_source_ids() -> List[str]:
    return [source["id"] for source in CURATED_SOURCE_CATALOG if source.get("default_selected")]


def get_sources_by_id(source_ids: Optional[List[str]]) -> List[Dict[str, Any]]:
    if not source_ids:
        source_ids = default_source_ids()
    wanted = set(source_ids)
    return [source for source in CURATED_SOURCE_CATALOG if source["id"] in wanted]


def source_catalog() -> Dict[str, Any]:
    return {
        "sources": CURATED_SOURCE_CATALOG,
        "default_source_ids": default_source_ids(),
        "source_groups": [
            {"id": "upload", "label": "Upload your own", "description": "Chemist-provided CSV/Excel rows."},
            {"id": "online", "label": "Pull online sources", "description": "Curated public datasets/APIs with provenance."},
            {"id": "auto", "label": "Auto-generate", "description": "CleanMol-created seed and candidate set when data is scarce."},
            {"id": "physics", "label": "Physics review", "description": "Optional FAIR Chemistry UMA readiness and atomistic review path."},
        ],
    }


def _recency_label(last_modified: str) -> str:
    if not last_modified:
        return "unknown_recency"
    try:
        dt = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - dt).days
    except ValueError:
        return "unknown_recency"
    if age_days <= 730:
        return "modern_or_recently_maintained"
    if age_days <= 1825:
        return "usable_but_review_recency"
    return "older_source_review_before_use"


def _domain_fit_from_text(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in ("antimicrobial", "antibacterial", "bioassay", "mic", "qac", "disinfectant")):
        return "high"
    if any(term in lowered for term in ("tox", "cytotoxic", "hemolysis", "safety")):
        return "safety_guardrail"
    if any(term in lowered for term in ("smiles", "chembl", "pubchem", "molecule")):
        return "generative_or_reference"
    return "review_needed"


def search_huggingface_sources(query: str, limit: int = 12, token: str = "") -> Dict[str, Any]:
    """Search Hugging Face datasets and annotate them for CleanMol Discovery."""
    if requests is None:
        return {"status": "dependency_missing", "results": [], "error": "requests is not installed"}

    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        resp = requests.get(
            "https://huggingface.co/api/datasets",
            params={"search": query, "limit": limit, "full": "true"},
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        return {"status": "error", "results": [], "error": str(exc)}

    results = []
    for item in payload[:limit]:
        dataset_id = item.get("id") or item.get("modelId") or ""
        tags = item.get("tags") or []
        text = " ".join([dataset_id, item.get("description") or "", " ".join(tags)])
        last_modified = item.get("lastModified") or item.get("last_modified") or ""
        results.append(
            {
                "id": f"hf:{dataset_id}",
                "name": dataset_id,
                "connector": "huggingface",
                "dataset_id": dataset_id,
                "role": "search_result",
                "domain_fit": _domain_fit_from_text(text),
                "modernity": _recency_label(last_modified),
                "pull_supported": True,
                "default_selected": False,
                "downloads": item.get("downloads"),
                "likes": item.get("likes"),
                "last_modified": last_modified,
                "tags": tags,
                "source_url": f"https://huggingface.co/datasets/{dataset_id}",
                "use_guidance": "Search result; inspect provenance and labels before trusting it for activity modeling.",
            }
        )

    return {"status": "success", "results": results}
