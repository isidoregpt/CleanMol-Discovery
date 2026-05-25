from __future__ import annotations

import csv
from pathlib import Path

from cleanmol.backend.app.integrations.rdkit_baseline import fingerprint_smiles


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    input_path = repo_root / "benchmarks" / "known_disinfectants" / "input.csv"
    _, rdkit_error = fingerprint_smiles("C")
    if rdkit_error == "rdkit_unavailable":
        report = repo_root / "benchmarks" / "results" / "benchmark_report.md"
        report.write_text(
            "# Benchmark Report\n\n"
            "Status: skipped because RDKit is not available in this Python environment.\n\n"
            "Install CleanMol Core dependencies, then rerun `python -m cleanmol.benchmarks.run_all`.\n",
            encoding="utf-8",
        )
        print("Benchmark sanity checks skipped: RDKit unavailable.")
        return 0
    rows = list(csv.DictReader(input_path.open("r", encoding="utf-8")))
    invalid = []
    valid = 0
    for row in rows:
        _, error = fingerprint_smiles(row["smiles"].split(".")[0])
        if row["expected_group"] == "invalid":
            if error != "invalid_smiles":
                invalid.append(row["name"])
        elif error:
            invalid.append(row["name"])
        else:
            valid += 1
    report = repo_root / "benchmarks" / "results" / "benchmark_report.md"
    report.write_text(
        "# Benchmark Report\n\n"
        "Status: sanity check completed.\n\n"
        f"Valid or expected-invalid rows checked: {len(rows)}\n\n"
        f"Valid benchmark structures: {valid}\n\n"
        f"Unexpected failures: {', '.join(invalid) if invalid else 'none'}\n\n"
        "This report is not a validation claim.\n",
        encoding="utf-8",
    )
    if invalid:
        print(f"Unexpected benchmark failures: {', '.join(invalid)}")
        return 1
    print(f"Benchmark sanity checks passed for {len(rows)} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
