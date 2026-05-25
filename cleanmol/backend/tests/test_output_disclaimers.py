from pathlib import Path

from app.discovery_automation import run_discovery_automation


def test_discovery_packet_writes_disclaimer_and_run_environment(tmp_path: Path):
    result = run_discovery_automation(
        str(tmp_path),
        keys={},
        options={
            "include_public_sources": False,
            "allow_builtin_generator": True,
            "target_candidate_count": 10,
            "reduced_egress": True,
        },
    )

    assert result["ok"] is True
    disclaimer = Path(result["files"]["disclaimer"])
    run_environment = Path(result["files"]["run_environment"])
    ranked = Path(result["files"]["ranked_hypothesis_candidates"])
    workbook = Path(result["files"]["ranked_hypothesis_candidates_review"])

    assert disclaimer.exists()
    assert "early-stage research triage tool" in disclaimer.read_text(encoding="utf-8")
    assert run_environment.exists()
    assert ranked.exists()
    assert workbook.exists()
