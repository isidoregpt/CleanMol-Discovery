import pytest

from app.integrations.rdkit_baseline import fingerprint_smiles
from app.smiles_validation import validate_and_enrich_smiles


pytestmark = pytest.mark.skipif(fingerprint_smiles("C")[1] == "rdkit_unavailable", reason="RDKit unavailable")


def test_smiles_validation_marks_valid_and_invalid_rows():
    molecules = [
        {"molecule_id": "valid", "smiles": "CCCCCCCCCCCC[N+](C)(C)C"},
        {"molecule_id": "invalid", "smiles": "not_a_smiles"},
    ]
    stats = validate_and_enrich_smiles(molecules)
    assert stats["valid_smiles"] == 1
    assert stats["invalid_smiles"] == 1
    assert molecules[0]["smiles_valid"] is True
    assert molecules[0]["candidate_tier"] == "modern_seed"
    assert molecules[1]["smiles_valid"] is False
