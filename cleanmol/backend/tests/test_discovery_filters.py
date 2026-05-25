from app.discovery_filters import enrich_modern_discovery_fields, is_generation_seed, is_legacy_or_low_priority


def test_qac_is_modern_generation_seed():
    molecule = {"name_as_written": "C12 QAC", "smiles": "CCCCCCCCCCCC[N+](C)(C)C"}
    enrich_modern_discovery_fields(molecule)
    assert molecule["candidate_tier"] == "modern_seed"
    assert is_generation_seed(molecule)
    assert "quaternary_ammonium" in molecule["modern_scaffold_tags"]


def test_neutral_monoamine_is_low_priority_reference():
    molecule = {"name_as_written": "butylamine", "smiles": "CCCCN"}
    enrich_modern_discovery_fields(molecule)
    assert molecule["candidate_tier"] == "legacy_or_low_priority"
    assert is_legacy_or_low_priority(molecule)
    assert "neutral_single_nitrogen" in molecule["legacy_flags"]
