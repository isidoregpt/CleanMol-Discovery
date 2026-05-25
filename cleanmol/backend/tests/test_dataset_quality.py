from app.dataset_quality import assess_dataset_quality


def test_dataset_quality_labels_tiny_synthetic_packet_not_ready():
    report = assess_dataset_quality(
        activity_rows=[{"smiles": "CCCC[N+](C)(C)C", "value": 8, "source": "unit"}],
        toxicity_rows=[],
        seeds=[{"smiles": "CCCC[N+](C)(C)C", "generation_provenance": "starter_prior"}],
        ranked_rows=[{"smiles": "CCCC[N+](C)(C)C", "candidate_tier": "modern_seed", "generation_provenance": "rule_based_de_novo_prior"}],
        manifests=[{"source": "unit", "status": "loaded"}],
    )
    assert report["status"] == "not_ready"
    assert "equalizer_note" in report
    assert report["gates_total"] == 10
