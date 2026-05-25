from app.integrations.chemprop_v2 import chemprop_status, score_with_chemprop_if_available


def test_chemprop_status_is_scaffolded_not_active():
    status = chemprop_status({})
    assert status["status"] in {"optional", "disabled"}
    assert "scaffolded" in status["message"] or status["status"] == "disabled"


def test_chemprop_scoring_fallback_is_explicit():
    result = score_with_chemprop_if_available()
    assert result["chemprop_prediction_status"] == "not_configured"
    assert result["chemprop_score_provenance"] == "chemprop_v2_optional_not_used"
    assert "Morgan fingerprint baseline" in result["warning"]
