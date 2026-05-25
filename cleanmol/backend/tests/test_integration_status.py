from app.integrations.status import get_integration_status


def test_core_status_rows_are_present():
    status = get_integration_status({}, {})
    for key in [
        "cleanmol_core",
        "rdkit",
        "morgan_baseline",
        "chemprop_v2",
        "reinvent4",
        "fairchem_uma",
        "anthropic_api",
        "openai_api",
        "google_gemini_api",
        "huggingface_api",
    ]:
        assert key in status
        assert "status" in status[key]
        assert "message" in status[key]


def test_reduced_egress_disables_provider_rows():
    status = get_integration_status(
        {"anthropic": "sk-ant-test", "openai": "sk-test", "gemini": "AIza-test", "hf": "hf_test"},
        {"reduced_egress": True},
    )
    assert status["anthropic_api"]["status"] == "disabled"
    assert status["openai_api"]["status"] == "disabled"
    assert status["google_gemini_api"]["status"] == "disabled"
    assert status["huggingface_api"]["status"] == "disabled"


def test_optional_integrations_can_be_disabled():
    status = get_integration_status({}, {"disabled_integrations": ["chemprop_v2", "reinvent4", "fairchem_uma"]})
    assert status["chemprop_v2"]["status"] == "disabled"
    assert status["reinvent4"]["status"] == "disabled"
    assert status["fairchem_uma"]["status"] == "disabled"
