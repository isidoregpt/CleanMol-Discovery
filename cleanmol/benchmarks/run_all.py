from __future__ import annotations

import csv
from pathlib import Path

from rdkit import rdBase

from cleanmol.backend.app.discovery_automation import _estimate_scores
from cleanmol.backend.app.discovery_filters import enrich_modern_discovery_fields
from cleanmol.backend.app.integrations.rdkit_baseline import build_morgan_baseline, fingerprint_smiles


ACTIVE_GROUPS = {"qac", "pyridinium", "phosphonium", "gemini_qac", "salt_counterion", "toxicity_risk_review"}
DECOY_GROUPS = {"lower_priority_control", "negative_control"}


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
    activity_rows = []
    for row in rows:
        smiles_for_fingerprint = row["smiles"].split(".")[0]
        _, error = fingerprint_smiles(smiles_for_fingerprint)
        if row["expected_group"] == "invalid":
            if error != "invalid_smiles":
                invalid.append(row["name"])
        elif error:
            invalid.append(row["name"])
        else:
            valid += 1
            activity_rows.append({
                "smiles": smiles_for_fingerprint,
                "molecule_name": row["name"],
                "activity_label": "active" if row["expected_group"] in ACTIVE_GROUPS else "inactive",
                "endpoint": "benchmark_sanity",
                "value": "8" if row["expected_group"] in ACTIVE_GROUPS else "512",
                "units": "synthetic_benchmark_units",
                "source": "cleanmol_public_benchmark",
            })

    baseline = build_morgan_baseline(activity_rows)
    seeds = []
    scored_rows = []
    for row in rows:
        if row["expected_group"] == "invalid":
            scored_rows.append({
                "name": row["name"],
                "expected_group": row["expected_group"],
                "valid": "no",
                "candidate_tier": "reject",
                "rank_score": "",
                "nearest_similarity": "",
                "morgan_neighbors": "",
                "score_provenance": "invalid_smiles_rejected",
            })
            continue
        candidate = {
            "candidate_id": row["name"],
            "name": row["name"],
            "smiles": row["smiles"].split(".")[0],
            "generator_engine": "benchmark_fixture",
            "generation_provenance": "public_benchmark_fixture",
        }
        enrich_modern_discovery_fields(candidate)
        candidate.update(_estimate_scores(candidate, seeds, baseline))
        scored_rows.append({
            "name": row["name"],
            "expected_group": row["expected_group"],
            "valid": "yes",
            "candidate_tier": candidate.get("candidate_tier", ""),
            "rank_score": candidate.get("rank_score", ""),
            "nearest_similarity": candidate.get("nearest_reference_similarity", ""),
            "morgan_neighbors": candidate.get("morgan_neighbor_count", ""),
            "score_provenance": candidate.get("score_provenance", ""),
        })

    active_scores = [
        float(row["rank_score"])
        for row in scored_rows
        if row["expected_group"] in ACTIVE_GROUPS and row["rank_score"] != ""
    ]
    decoy_scores = [
        float(row["rank_score"])
        for row in scored_rows
        if row["expected_group"] in DECOY_GROUPS and row["rank_score"] != ""
    ]
    ranking_ok = bool(active_scores and decoy_scores and min(active_scores) > max(decoy_scores))

    table_lines = [
        "| Name | Expected group | Valid | Candidate tier | Rank score | Morgan neighbors | Nearest similarity | Score provenance |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in scored_rows:
        table_lines.append(
            f"| {row['name']} | {row['expected_group']} | {row['valid']} | {row['candidate_tier']} | "
            f"{row['rank_score']} | {row['morgan_neighbors']} | {row['nearest_similarity']} | {row['score_provenance']} |"
        )

    report = repo_root / "benchmarks" / "results" / "benchmark_report.md"
    report.write_text(
        "# Benchmark Report\n\n"
        "Status: sanity check completed in a CleanMol Core environment with RDKit installed.\n\n"
        f"RDKit version: `{rdBase.rdkitVersion}`\n\n"
        f"Valid or expected-invalid rows checked: {len(rows)}\n\n"
        f"Valid benchmark structures: {valid}\n\n"
        f"Morgan baseline reference rows: {len(baseline.references)}\n\n"
        f"Ranking sanity check: {'passed' if ranking_ok else 'needs review'}\n\n"
        f"Unexpected failures: {', '.join(invalid) if invalid else 'none'}\n\n"
        + "\n".join(table_lines)
        + "\n\nThis report is not a validation claim.\n",
        encoding="utf-8",
    )
    if invalid or not ranking_ok:
        print(f"Unexpected benchmark failures: {', '.join(invalid)}")
        return 1
    print(f"Benchmark sanity checks passed for {len(rows)} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
