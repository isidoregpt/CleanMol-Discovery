from pathlib import Path

from app.discovery_automation import _run_reinvent_if_available


def test_reinvent_disabled_status_is_consistent(tmp_path: Path):
    candidates, meta = _run_reinvent_if_available(
        tmp_path,
        seeds=[{"smiles": "CCCC[N+](C)(C)C", "molecule_id": "seed"}],
        target_count=5,
        timeout_seconds=1,
        enabled=False,
    )
    assert candidates == []
    assert meta["status"] == "disabled"


def test_reinvent_missing_or_config_status_is_consistent(tmp_path: Path):
    candidates, meta = _run_reinvent_if_available(
        tmp_path,
        seeds=[{"smiles": "CCCC[N+](C)(C)C", "molecule_id": "seed"}],
        target_count=5,
        timeout_seconds=1,
        config_path=str(tmp_path / "missing.toml"),
    )
    assert candidates == []
    assert meta["status"] in {"not_installed", "config_missing"}
