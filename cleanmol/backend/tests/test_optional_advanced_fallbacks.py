from pathlib import Path

from app.integrations.chemprop_v2 import score_with_chemprop_if_available
from app.integrations.fairchem_uma import UMA_WARNING, handoff_message
from app.integrations.reinvent4 import detect_reinvent4, write_seed_file


def test_chemprop_placeholder_returns_safe_fallback_warning():
    result = score_with_chemprop_if_available()
    assert result["chemprop_prediction_status"] == "not_configured"
    assert "Morgan fingerprint baseline" in result["warning"]


def test_reinvent_seed_file_writer(tmp_path: Path):
    path = write_seed_file(tmp_path / "seeds.smi", [{"smiles": "CCCC[N+](C)(C)C", "molecule_id": "seed"}])
    assert path.read_text(encoding="utf-8").strip() == "CCCC[N+](C)(C)C\tseed"


def test_reinvent_detection_is_safe_without_config():
    status = detect_reinvent4("")
    assert status["status"] in {"not_installed", "installed_but_not_configured"}


def test_fairchem_handoff_language_is_claim_controlled():
    assert "does not run UMA by default" in handoff_message()
    assert "does not prove antimicrobial activity" in UMA_WARNING
