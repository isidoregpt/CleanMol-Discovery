# FairChem and UMA Integration Notes

CleanMol extracts literature-grounded chemistry datasets. FairChem UMA is a downstream atomistic modeling path, not a replacement for CleanMol's extraction/audit LLMs.

For the actual "Lysol 2.0" discovery model/dataset choice, see `lysol_2_discovery_strategy.md`. The short version: UMA/OMol25 is the best physics layer, but the primary antimicrobial discovery loop should use CleanMol-curated QAC/biocide activity data plus PubChem BioAssay, ChEMBL, and toxicity/selectivity datasets.

## Why UMA Matters

FAIRChem describes UMA as a universal machine-learning potential for molecules, materials, and catalysts. The UMA docs say the model routes on task, total charge, spin multiplicity, and elemental composition. For CleanMol's current QAC/biocide scope, the closest UMA task is usually `omol`, because it targets organic molecules and molecular chemistry.

Useful sources:

- UMA guide: https://fair-chem.github.io/uma/
- FairChem docs: https://fair-chem.github.io/
- UMA model repo: https://huggingface.co/facebook/UMA
- Leaderboard Space: https://huggingface.co/spaces/facebook/fairchem_leaderboard

## CleanMol Output Added For This Path

The merge/export stage now writes:

```text
fairchem_uma_candidates.csv
```

CleanMol also writes:

```text
candidate_generation_seed.smi
legacy_or_low_priority_molecules.csv
screening_score_profile.json
```

Use `candidate_generation_seed.smi` for modern disinfectant generation work. Use
`legacy_or_low_priority_molecules.csv` as baseline, negative, or activity-reference material. Do not use
`molecules.smi` as the primary generation seed file unless a chemist has reviewed the candidate tiers.

This file deduplicates validated SMILES and gives each molecule:

- `uma_task`: currently `omol`
- `total_charge_hint`: RDKit formal charge when available, defaulting to `0`
- `spin_multiplicity_hint`: default `1`
- `fragment_count` and `atom_count`
- `readiness_status` and `readiness_notes`

The important statuses are:

- `candidate`: likely suitable for RDKit 3D conformer generation before UMA.
- `needs_structure_review`: RDKit charge/fragment metadata is missing; rerun validation with RDKit.
- `needs_charge_review`: charged molecule; confirm `total_charge` and spin before UMA.
- `needs_fragment_review`: salt/counterion or disconnected fragments; decide whether to model the full explicit salt or a selected active fragment.
- `invalid_smiles` or `missing_smiles`: not ready for atomistic modeling.

## What We Should Not Automate Yet

Do not auto-submit CleanMol outputs to the FairChem leaderboard. The leaderboard expects benchmark prediction files from a model evaluation run, not literature-extracted molecule tables. CleanMol can prepare candidate molecules and provenance, but a separate runner should:

1. Generate or import 3D atomistic structures.
2. Confirm charge and spin multiplicity.
3. Run FairChem/UMA or a competing model on the relevant benchmark task.
4. Produce the exact prediction file expected by the leaderboard docs.
5. Submit only after the user reviews model metadata and visibility.

## Leaderboard API Shape

Validated on May 4, 2026:

- API schema: `GET https://facebook-fairchem-leaderboard.hf.space/gradio_api/info`
- Config: `GET https://facebook-fairchem-leaderboard.hf.space/config`
- Current submit endpoint: `/add_new_eval`
- Current dependency id for `/add_new_eval`: `2`

Always fetch `/config` at submission time and find `dependencies[i].id` where `api_name == "add_new_eval"`, because Gradio ids can change.

`/add_new_eval` currently accepts data in this order:

1. uploaded file object
2. eval type
3. organization
4. model name
5. model/checkpoint URL
6. paper URL
7. energy conserving boolean
8. total energy model boolean
9. contact email
10. training set
11. additional info
12. submission visibility

File upload:

```text
POST https://facebook-fairchem-leaderboard.hf.space/gradio_api/upload
Authorization: Bearer $HF_TOKEN
files=@prediction_file.ext
```

Use the returned path as:

```json
{
  "path": "<returned-path>",
  "meta": { "_type": "gradio.FileData" },
  "orig_name": "prediction_file.ext"
}
```

Queue submit:

```text
POST https://facebook-fairchem-leaderboard.hf.space/gradio_api/queue/join
GET  https://facebook-fairchem-leaderboard.hf.space/gradio_api/queue/data?session_hash=<same-uuid>
```

Authentication requires a Hugging Face token from https://huggingface.co/settings/tokens. UMA model checkpoints are gated, so the user must request access to `facebook/UMA` before local model use.
