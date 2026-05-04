# Automated Discovery Workflow

CleanMol now has an automated Discovery option for two user groups:

1. Chemists who already have a dataset.
2. Researchers who do not have the time, funding, or institutional access to build one from scratch.

The goal is to level the starting line without hiding uncertainty. CleanMol can create and rank molecule hypotheses,
but a qualified chemist still needs to review candidates before any lab work.

## Modes

### 1. Upload Your Own

A chemist can upload `.csv`, `.tsv`, `.xlsx`, or `.xlsm` data. CleanMol looks for common columns such as:

- `smiles`
- `name` or `compound_name`
- `organism`
- `assay_type`
- `endpoint`
- `value`
- `units`
- `MIC`
- toxicity or Tox21-style columns

CleanMol normalizes these into the same training tables used by automated mode.

### 2. Pull Online Sources

CleanMol has a Source Library for chemists who do not want to touch APIs. It lists curated sources with:

- domain fit
- modernity/recency label
- source role
- pull support
- plain-English use guidance

CleanMol also has a Hugging Face dataset search box. Search results are labeled as `high`, `safety_guardrail`,
`generative_or_reference`, or `review_needed`, and they get a recency label when the Hub provides update metadata.

Initial curated sources:

- `scbirlab/stokes-2020-ai` for antibacterial activity reference data.
- `scikit-fingerprints/MoleculeNet_Tox21` for toxicity/selectivity labels.
- `antoinebcx/smiles-molecules-chembl` as a broad generative prior.
- `maomlab/ChAFF` for assay-interference/liability flags.
- ChEMBL antimicrobial MIC/MBC rows through ChEMBL Data Web Services.
- PubChem BioAssay is cataloged for source discovery; fully automated topical AID pulls need curated AID selection.

CleanMol favors modern/currently maintained sources, but older benchmark datasets can still be useful as safety
guardrails or baselines. They are not allowed to dominate modern disinfectant seed selection.

### 3. Auto-Generate Data

- extracted literature rows from `analysis_ready.csv`
- `candidate_generation_seed.smi`
- public Hugging Face/API datasets when enabled
- transparent synthetic/model-prior seed molecules when needed

If no extracted dataset exists yet, CleanMol starts from modern cationic/amphiphilic starter scaffolds and clearly marks
the resulting rows as priors rather than experimental facts.

## Outputs

Discovery writes files under:

```text
<output_dir>/discovery/
```

Key files:

- `training_activity_table.csv`
- `training_toxicity_table.csv`
- `resolved_generation_seeds.smi`
- `ranked_lab_candidates.csv`
- `ranked_lab_candidates_review.xlsx`
- `discovery_source_manifest.json`
- `dataset_quality_report.json`
- `discovery_run_summary.json`

If Excel dependencies are unavailable, CleanMol writes a CSV review packet instead.

## How Generation Works

CleanMol tries the strongest available path first:

1. Use REINVENT 4 if the `reinvent` executable is installed and a local `reinvent.toml` is present.
2. Fall back to CleanMol's built-in de novo generator for modern disinfectant-like scaffolds.

The built-in generator creates QAC, benzyl-QAC, phosphonium, pyridinium, and gemini/bis-QAC variants across reviewed
tail/linker ranges. These are not synthesis instructions and are not efficacy claims; they are candidate hypotheses
for scoring and chemist review.

## How Scoring Works

CleanMol trains a lightweight nearest-neighbor baseline from the available activity and toxicity rows. If the dataset is
empty, it uses transparent heuristic priors from the modern-disinfectant score profile.

Scores include:

- `rank_score`
- `predicted_activity_score`
- `predicted_selectivity_score`
- `predicted_toxicity_risk`
- `novelty_score`
- `uncertainty`
- `candidate_tier`
- `generation_recommendation`
- `uma_readiness_status`

Rows generated from synthetic/model priors are marked with provenance so they do not get confused with lab data.

## Dataset Quality Equalizer

CleanMol now applies the same quality gates to uploaded and auto-created datasets. A no-resource user gets the same
experience and review standard as a user with a private curated dataset, but CleanMol will not pretend that synthetic
priors are the same as measured evidence.

Quality statuses:

- `Curated-Grade`: strong enough to treat as a serious model-training/review packet.
- `Strong Starter`: useful and fairly broad, but still has important gaps.
- `Useful Starter`: good for exploration, not yet strong enough for high-confidence training.
- `Not Ready`: needs more measured/public data before candidate claims should be trusted.

Quality gates check:

- activity evidence depth
- toxicity/selectivity depth
- label density
- source diversity
- modern/current source presence
- organism or assay breadth
- modern seed depth
- scaffold diversity
- synthetic-prior separation
- ranked candidate quality

The report is written to `dataset_quality_report.json` and included in the review workbook.

## What Still Needs Qualified Review

Every `ranked_lab_candidates.csv` row should be reviewed for:

- structure validity
- salt/counterion treatment
- total charge and spin multiplicity before UMA
- known hazards or structural liabilities
- formulation fit
- novelty versus nearest known analogs
- whether the supporting data is experimental, public-dataset-derived, or synthetic/model-prior

CleanMol deliberately does not provide synthesis routes or claim disinfectant performance.

## Sources

- REINVENT 4: https://github.com/MolecularAI/REINVENT4
- Chemprop: https://chemprop.readthedocs.io/
- FAIR Chemistry install: https://fair-chem.github.io/install/
- FAIR Chemistry UMA: https://fair-chem.github.io/uma/
- OMol25: https://fair-chem.github.io/omol25/
- Hugging Face Dataset Viewer API: https://datasets-server.huggingface.co
- Hugging Face Hub search: https://huggingface.co/docs/hub/search
- ChEMBL Data Web Services: https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services
- PubChem PUG REST: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
