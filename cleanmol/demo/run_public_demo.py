"""Create a no-key synthetic CleanMol public review demo packet."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run_demo(output_dir: str | Path | None = None) -> dict:
    root = repo_root()
    source = root / "samples" / "public_review_demo"
    if output_dir is None:
        output = Path.home() / "CleanMol" / "output" / "public_review_demo"
    else:
        output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    target = output / "public_review_demo"
    if target.resolve() == source.resolve():
        target = output / "public_review_demo_run"
    shutil.copytree(source, target, dirs_exist_ok=True)

    summary = {
        "status": "success",
        "demo_type": "synthetic_public_review_demo",
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "output_dir": str(target),
        "requires_api_keys": False,
        "warning": "Synthetic demo only. Not measured antimicrobial evidence.",
    }
    (target / "DEMO_RUN_SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CleanMol no-key public demo.")
    parser.add_argument("--output-dir", default=None, help="Directory where the demo packet should be written.")
    args = parser.parse_args()
    summary = run_demo(args.output_dir)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
