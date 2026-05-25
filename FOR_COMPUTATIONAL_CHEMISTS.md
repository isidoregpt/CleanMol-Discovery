# CleanMol Discovery for Computational Chemists

CleanMol Core keeps the default install light and reliable. Chemprop v2, REINVENT 4, and FairChem/UMA are optional integrations and must not be treated as required runtime dependencies.

## Core Scoring

Default ranking uses:

- heuristic disinfectant discovery profile
- RDKit SMILES validation and descriptors
- RDKit Morgan fingerprint nearest-neighbor baseline
- Dataset Quality Equalizer
- provenance and limitation fields on every ranked row

Rows include nearest-reference fields, Morgan score provenance, score source lists, and the warning that rank scores are not probabilities.

## Optional Chemprop v2

Chemprop v2 is optional. CleanMol detects installation and model checkpoint availability. If Chemprop is missing, unconfigured, or errors, the run continues with RDKit Morgan baseline and heuristic triage scoring.

Use the Advanced Discovery Pack script only when you want a separate advanced environment:

- Windows: `setup/windows/4-install-advanced-discovery-pack.bat`
- Mac: `setup/mac/4-install-advanced-discovery-pack.command`

## Optional REINVENT 4

REINVENT 4 is optional and guided. CleanMol can write seed files and detect a local `reinvent` executable and config path. If REINVENT is missing or fails, CleanMol uses the built-in rule-based hypothesis generator.

## FairChem / UMA

CleanMol prepares a FairChem/UMA review handoff file. It does not run UMA by default.

UMA is an atomistic plausibility and structure-review resource. It does not prove antimicrobial activity, safety, synthesis feasibility, or regulatory readiness.

## Reduced-Egress Mode

Reduced-egress / local-only mode disables provider LLM calls, Hugging Face/API pulling, and online source search. Use it for institutional review or local uploaded-data workflows.
