# Public Review Demo Packet

This folder contains a small synthetic CleanMol Discovery output packet for reviewers.

It is included so a chemist can see what the app produces without needing API keys, private papers, or a long model run.

## Important

These rows are demo data. They are not measured antimicrobial results, not safety results, and not synthesis recommendations.

The scores are illustrative examples of CleanMol output shape. They should not be used to choose real lab candidates.

## Suggested Review Order

1. Open `discovery/dataset_quality_report.json`.
2. Open `discovery/discovery_source_manifest.json`.
3. Open `discovery/ranked_lab_candidates.csv`.
4. Open `discovery/ranked_lab_candidates_review.csv`.
5. Open `fairchem_uma_candidates.csv`.
6. Read `PUBLIC_REVIEW_DISCLAIMER.md` in the repository root.

## What This Packet Demonstrates

- candidate ranking columns
- quality-gate reporting
- source manifest provenance
- modern disinfectant scaffold tags
- UMA readiness statuses
- clear marking of synthetic/model-prior limitations

## What This Packet Does Not Demonstrate

- measured antimicrobial efficacy
- validated toxicity predictions
- synthesis planning
- regulatory readiness
- commercial product suitability
- real FAIR Chemistry / UMA results

## Included Files

```text
samples/public_review_demo/
  README.md
  candidate_generation_seed.smi
  fairchem_uma_candidates.csv
  legacy_or_low_priority_molecules.csv
  screening_score_profile.json
  discovery/
    training_activity_table.csv
    training_toxicity_table.csv
    resolved_generation_seeds.smi
    ranked_lab_candidates.csv
    ranked_lab_candidates_review.csv
    discovery_source_manifest.json
    dataset_quality_report.json
    discovery_run_summary.json
```
