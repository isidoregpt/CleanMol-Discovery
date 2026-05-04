# CleanMol Discovery

CleanMol is a literature-grounded chemistry dataset builder for QAC/biocide discovery.

## 2026 Discovery Direction

The app now treats "molecule with nitrogen" and "modern disinfectant seed" as different things. During SMILES
validation and merge export, molecules are tagged with:

- `modern_disinfectant_score`
- `candidate_tier`
- `modern_scaffold_tags`
- `legacy_flags`
- `generation_recommendation`

Neutral single-nitrogen amines and simple monoamines are kept as baseline/activity-reference molecules, not primary
generation seeds. Modern seed candidates prioritize stable cationic/amphiphilic scaffolds such as quaternary
ammonium, gemini/bis-cationic QACs, phosphonium, imidazolium, pyridinium, guanidinium, sulfonium, and zwitterionic
surfactant-like structures.

Recommended discovery stack:

- Activity model: Chemprop v2 multitask ensemble plus a Morgan-fingerprint baseline.
- Generator: REINVENT 4 with a multi-objective score profile.
- Physics filter: FAIRChem UMA with task `omol` and OMol25-style charge/spin-aware inputs.
- Data: CleanMol-curated QAC/biocide literature plus PubChem BioAssay, ChEMBL, Tox21/ToxCast, EPA CompTox, and
  hemolysis/selectivity assays.

Key exports:

- `analysis_ready.csv`
- `molecules.smi`
- `candidate_generation_seed.smi`
- `legacy_or_low_priority_molecules.csv`
- `screening_score_profile.json`
- `fairchem_uma_candidates.csv`
- `discovery/ranked_lab_candidates.csv`
- `discovery/ranked_lab_candidates_review.xlsx`

The Discovery Automation panel now has three paths: upload your own dataset, pull from a curated/searchable online
Source Library, or auto-generate a usable 2026 starter dataset/candidate packet from CleanMol extracts, public sources,
and transparent synthetic/model-prior seeds.

The Dataset Quality Equalizer applies the same gates to uploaded and auto-created datasets, then labels the packet as
Curated-Grade, Strong Starter, Useful Starter, or Not Ready.

See the strategy, automated discovery, and FairChem/UMA notes in the app docs folder.

## License

CleanMol Discovery is licensed under the GNU Affero General Public License v3.0 only (`AGPL-3.0-only`).

That license allows use, modification, distribution, and resale, but redistributed or network-hosted modified versions
must provide corresponding source code under the same license. This is intentional: the project is meant to stay usable
by under-resourced researchers, not disappear into closed repackaged products.

The CleanMol Discovery and CleanMol names are not licensed for misleading resale, endorsement, or branding of forks.
See `TRADEMARKS.md` and `NOTICE`.
