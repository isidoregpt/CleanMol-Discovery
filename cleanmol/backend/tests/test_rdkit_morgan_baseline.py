import pytest

from app.integrations.rdkit_baseline import (
    build_morgan_baseline,
    fingerprint_smiles,
    score_candidate_against_baseline,
)


pytestmark = pytest.mark.skipif(fingerprint_smiles("C")[1] == "rdkit_unavailable", reason="RDKit unavailable")


def test_valid_smiles_fingerprint_generation():
    fingerprint, error = fingerprint_smiles("CCCCCCCCCCCC[N+](C)(C)C")
    assert error is None
    assert fingerprint is not None


def test_invalid_smiles_handling():
    fingerprint, error = fingerprint_smiles("not_a_smiles")
    assert fingerprint is None
    assert error == "invalid_smiles"


def test_similar_qac_molecules_score_as_neighbors():
    baseline = build_morgan_baseline([
        {
            "smiles": "CCCCCCCCCCCC[N+](C)(C)C",
            "molecule_name": "C12 QAC reference",
            "activity_label": "active",
            "endpoint": "MIC",
            "value": "8",
            "units": "ug/mL",
            "source": "unit_test",
        }
    ])
    result = score_candidate_against_baseline("CCCCCCCCCC[N+](C)(C)C", baseline)
    assert result["morgan_neighbor_count"] >= 1
    assert result["nearest_reference_name"] == "C12 QAC reference"
    assert result["nearest_reference_similarity"] > 0.45
    assert result["morgan_score_provenance"] == "rdkit_morgan_fingerprint_baseline_plus_discovery_profile"


def test_unrelated_neutral_molecules_score_low_or_no_neighbor():
    baseline = build_morgan_baseline([
        {"smiles": "CCCCCCCCCCCC[N+](C)(C)C", "activity_label": "active", "source": "unit_test"}
    ])
    result = score_candidate_against_baseline("c1ccccc1", baseline, min_similarity=0.01)
    assert result["nearest_reference_similarity"] < 0.25


def test_no_neighbor_case_is_graceful_and_has_provenance():
    baseline = build_morgan_baseline([
        {"smiles": "CCCCCCCCCCCC[N+](C)(C)C", "activity_label": "active", "source": "unit_test"}
    ])
    result = score_candidate_against_baseline("O", baseline, min_similarity=0.9)
    assert result["morgan_neighbor_count"] == 0
    assert result["morgan_baseline_score"] is None
    assert result["morgan_score_provenance"] == "heuristic_prior_no_reference_neighbors_available"
