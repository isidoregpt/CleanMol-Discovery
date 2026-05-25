# CleanMol Discovery for Chemists

CleanMol Discovery is an early-stage research triage tool. It helps organize chemistry data, generate disinfectant-relevant molecular hypotheses, and prioritize candidates for expert review. It does not prove antimicrobial activity, safety, synthesizability, formulation stability, environmental acceptability, regulatory compliance, or commercial suitability.

## The Simplest Path

1. Open `setup/windows` on a Windows PC or `setup/mac` on an Apple Silicon / M-Series Mac.
2. Run the install file for your operating system.
3. Run the start file for your operating system.
4. Open the local CleanMol page shown by the start script.
5. Choose an output folder.
6. Click `Run Synthetic Demo` first.
7. Open the demo output folder and read `DISCLAIMER.txt`, `run_environment.json`, `dataset_quality_report.json`, and the Excel review workbook.

## If You Have Papers

Use `Run Pipeline`.

You need:

- an input folder containing born-digital PDFs
- an output folder
- an Anthropic API key

CleanMol extracts structured molecule, experiment, result, evidence, SMILES, and review data. This is for dataset building, not proof that any molecule works.

## If You Have a Dataset

Use `Discovery Automation`, then choose `Chemist upload`.

You need:

- an output folder
- a CSV or Excel file with SMILES and activity or assay information

CleanMol applies the same Dataset Quality Equalizer and ranking fields used for auto-created datasets.

## If You Do Not Have a Dataset

Use `Discovery Automation`, then choose `Auto-create`.

CleanMol can combine existing CleanMol extracts, selected public sources, and transparent synthetic/model-prior seeds. The output is a starter research packet, not a replacement for expert curation.

## What To Trust First

Trust the packet structure, provenance, warning fields, and review workflow more than the rank number. Rank scores are triage scores. They are not probabilities and are not laboratory results.

## Files To Open First

- `DISCLAIMER.txt`
- `ranked_hypothesis_candidates_review.xlsx`
- `dataset_quality_report.json`
- `discovery_source_manifest.json`
- `run_environment.json`
