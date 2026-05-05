# Start Here: Public Review Guide

This page is for chemists, reviewers, and collaborators who want to understand CleanMol Discovery without becoming software engineers first.

## The Short Version

CleanMol helps turn messy chemistry information into a reviewable discovery packet.

It can:

1. extract chemistry data from PDFs
2. accept a chemist's own CSV or Excel dataset
3. pull from curated/searchable online sources
4. auto-create a starter discovery packet when a researcher has no dataset
5. rank candidate molecules for expert review
6. prepare a FAIR Chemistry / UMA readiness file for optional physics review

It does not prove that a molecule is effective, safe, synthesizable, regulatory-ready, or product-ready.

## What To Install

Choose your operating system.

### Windows

1. Install Python 3.10 or newer.
2. Install Node.js 20.9 or newer.
3. Open `setup\windows`.
4. Double-click `1-install-windows.bat`.
5. Double-click `2-run-windows.bat`.
6. Open the local web address shown in the terminal, usually:

```text
http://localhost:3000
```

When finished, double-click `3-end-windows.bat`.

### Apple Silicon / M-Series Mac

1. Install Python 3.10 or newer.
2. Install Node.js 20.9 or newer.
3. Open Terminal in the `setup/mac` folder.
4. Run:

```bash
chmod +x 1-install-mac.command 2-run-mac.command 3-end-mac.command
./1-install-mac.command
./2-run-mac.command
```

The Mac runner opens the app automatically when it can. If port 3000 is busy, it chooses the next open port.

When finished, run:

```bash
./3-end-mac.command
```

## What To Click

### If You Have PDFs

1. Put PDFs into the input folder.
2. Choose an output folder.
3. Add an Anthropic API key.
4. Click `Run Pipeline`.
5. Review the Excel workbook and exported CSV files.

Use this path when you want structured data from papers or patents.

### If You Have Your Own Dataset

1. Choose an output folder.
2. Go to `Discovery Automation`.
3. Select `Chemist upload`.
4. Upload your CSV or Excel file.
5. Click `Run Discovery`.
6. Review `discovery/ranked_lab_candidates_review.xlsx`.

Use this path when you trust your own measured data and want CleanMol to score, filter, and package it.

### If You Do Not Have A Dataset

1. Choose an output folder.
2. Go to `Discovery Automation`.
3. Select `Auto-create`.
4. Leave public sources enabled.
5. Click `Run Discovery`.
6. Start with `discovery/dataset_quality_report.json`.

Use this path to create a starter packet from public sources, Hugging Face/API discovery, CleanMol extracts, and transparent generated seeds.

## The Files That Matter Most

Start with these:

- `discovery/ranked_lab_candidates.csv`: the ranked candidate list
- `discovery/ranked_lab_candidates_review.xlsx`: the human review workbook when Excel export is available
- `discovery/dataset_quality_report.json`: the quality grade and failed gates
- `discovery/discovery_source_manifest.json`: where the data came from
- `candidate_generation_seed.smi`: generation seed molecules
- `legacy_or_low_priority_molecules.csv`: baseline or low-priority molecules kept for context
- `screening_score_profile.json`: how CleanMol weighted activity, toxicity, novelty, and scaffold relevance
- `fairchem_uma_candidates.csv`: optional FAIR Chemistry / UMA readiness review

## What Good Output Looks Like

Good output is not just a high score.

A useful packet should show:

- multiple independent sources
- measured activity rows, not only generated or SMILES-only rows
- toxicity or selectivity guardrails
- modern disinfectant-relevant scaffolds
- clear provenance for each row
- low or explainable uncertainty
- a `Curated-Grade`, `Strong Starter`, or clearly explained `Useful Starter` status
- candidate notes that make sense to a chemist
- FAIR Chemistry readiness notes for charged, fragmented, or salt-like molecules

## What Not To Over-Trust

Do not over-trust:

- a high `rank_score` without reviewing the source data
- synthetic/model-prior rows as if they were measured assays
- a candidate with unclear charge, salt, fragment, or counterion handling
- a packet labeled `Not Ready`
- a molecule that looks modern but has no safety/selectivity support
- FAIR Chemistry / UMA output as proof of antimicrobial activity
- any output as synthesis, safety, regulatory, or product guidance

## Suggested Public Review Checklist

Reviewers can use this checklist:

1. Can a non-technical chemist understand which path to choose?
2. Are required folders and API keys clear?
3. Are uploaded, public, and auto-created data treated with the same quality gates?
4. Are synthetic/demo rows labeled clearly?
5. Are the output files understandable?
6. Are limitations visible before a user reaches the candidate list?
7. Does the app avoid claiming efficacy, safety, or synthesis readiness?
8. Does the FAIR Chemistry / UMA path appear optional and appropriately cautious?

## Demo Packet

A small synthetic demo packet is included at:

```text
samples/public_review_demo/
```

It lets reviewers inspect the shape of the outputs without API keys, private papers, or a long model run.
