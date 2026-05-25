# Validation Status

CleanMol Discovery is a Public Research Preview.

## Implemented

- Local backend and frontend workflow
- PDF text extraction for born-digital PDFs
- LLM extraction pipeline when provider keys are supplied
- SMILES validation through RDKit
- RDKit Morgan fingerprint nearest-neighbor baseline
- Dataset Quality Equalizer
- Built-in rule-based hypothesis generator
- CSV and Excel review packet export
- Output disclaimers, provenance, and run metadata
- No-key synthetic demo packet

## Experimental

- Figure analysis
- Online source search and pulling
- Candidate ranking weights
- Dataset quality thresholds
- Optional advanced Chemprop and REINVENT integration scaffolding

## Handoff Only

- FairChem/UMA review files and readiness notes

CleanMol prepares handoff files but does not run UMA by default.

## Not Validated

CleanMol does not validate antimicrobial efficacy, toxicity, synthesis feasibility, formulation stability, regulatory compliance, environmental acceptability, patent clearance, or commercial suitability.

## Required Before Scientific Claims

- benchmark expansion against curated public disinfectant and decoy sets
- extraction benchmark against human-labeled paper sets
- external chemist review
- microbiology assay validation
- toxicology and formulation review
- regulatory review
