from pathlib import Path

from app.discovery_automation import run_discovery_automation


def test_discovery_automation_reduced_egress_uses_builtin_and_metadata(tmp_path: Path):
    result = run_discovery_automation(
        str(tmp_path),
        keys={},
        options={
            "include_public_sources": False,
            "allow_builtin_generator": True,
            "target_candidate_count": 10,
            "reduced_egress": True,
            "disabled_integrations": ["chemprop_v2", "reinvent4"],
        },
    )
    assert result["ok"] is True
    assert result["summary"]["ranked_count"] == 10
    assert result["summary"]["reinvent_status"] == "disabled"
    assert Path(result["files"]["ranked_hypothesis_candidates"]).exists()
