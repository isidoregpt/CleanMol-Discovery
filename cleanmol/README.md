# CleanMol Discovery - Chemistry Dataset Builder

CleanMol is a desktop application for Windows and Apple Silicon / M-Series Macs. It extracts structured chemistry datasets from born-digital PDFs and turns papers and patents into auditable records for molecules, experiments, numeric results, evidence snippets, SMILES enrichment, and review workbooks.

## Public Review Starting Points

If you are reviewing CleanMol for the first time, start with:

- `../PUBLIC_REVIEW_DISCLAIMER.md`
- `../SECURITY.md`
- `docs/start_here_public_review.md`
- `../samples/public_review_demo/`

The demo packet is synthetic and intentionally not ready for lab use. It shows the output shape without requiring API keys, private PDFs, or a model run.

Security reviewers should read `../SECURITY.md` before approving institutional use. CleanMol is designed for local workstation review, not shared enterprise hosting without additional controls.

## What It Produces

- SQLite database: `dataset.db`
- Per-document JSONL exports
- Combined Excel workbooks for review and downstream analysis
- Bundle folders containing page-anchored markdown, model outputs, provenance, logs, audits, repairs, gaps, and SMILES validation

## Pipeline

1. PDF extraction: create page-anchored markdown from each PDF.
2. Figure analysis: extract visible chemical structures and SMILES from figures.
3. Primary extraction: extract molecules, experiments, and results with citations.
4. OpenAI audit: verify each extracted claim against source text.
5. Auto-repair: re-extract ambiguous or rejected items.
6. Gap hunt: find missed molecules, tables, figures, protocols, and results.
7. Targeted gap resolution: fill high-value gaps with page-focused prompts.
8. SMILES lookup and validation: enrich via public chemistry services and RDKit.
9. Export: write SQLite, JSONL, `.smi`, and Excel review files.

## 2026 Default Models

The backend is the source of truth for model defaults. The app defaults to the latest provider frontier models when API keys are available by calling provider model-list APIs. If a key is missing, a provider is unreachable, or a selector cannot find a suitable frontier model, CleanMol uses verified fallback IDs for offline startup and reproducible records. Known old IDs are upgraded automatically. Fallbacks last verified against provider docs: 2026-05-04.

| Role | Default model | Why |
| --- | --- | --- |
| Primary extraction and repair | `claude-opus-4-7` | Strong long-context chemistry/literature reasoning |
| Figure analysis | `claude-opus-4-7` | Latest Anthropic frontier model for multimodal structure extraction |
| Audit | `gpt-5.5` | Strong reasoning and citation verification via the OpenAI Responses API |
| Gap hunt | `gemini-3.1-pro-preview` | Long-context coverage checks over full papers |

The Models panel keeps `Use latest provider models by default` enabled. A chemist can click `Refresh latest` to re-check providers immediately, or turn the option off to run exactly the visible model IDs.

## Discovery Model And Dataset Recommendation

For the "Lysol 2.0" goal, do not use a single generic chemistry dataset as the backbone. Use CleanMol to build a disinfectant-specific activity dataset, then combine it with public bioactivity and toxicity data.

- The `Discovery Automation` panel can now auto-create a dataset/candidate packet or accept a chemist-uploaded CSV/Excel dataset.
- Automated mode can pull configured Hugging Face/API sources, use extracted CleanMol data, create transparent synthetic/model-prior seeds when needed, generate candidates, score them, and write a ranked review packet.
- The `Source Library` shows curated online sources and Hugging Face search results with domain-fit, modernity, and pull-status labels for non-technical chemists.
- The `Dataset Quality Equalizer` applies the same gates to uploaded and auto-created datasets and labels the packet as Curated-Grade, Strong Starter, Useful Starter, or Not Ready.
- CleanMol now separates modern generation seeds from legacy/simple nitrogen compounds with `modern_disinfectant_score`, `candidate_tier`, `modern_scaffold_tags`, `legacy_flags`, and `generation_recommendation`.
- Neutral single-nitrogen amines and simple monoamines are exported as baseline/activity-reference material, not as primary generation seeds.
- Modern seed candidates prioritize stable cationic/amphiphilic scaffolds: QACs, gemini/bis-cationic QACs, phosphonium, imidazolium, pyridinium, guanidinium, sulfonium, and zwitterionic surfactant-like structures.
- Primary activity data: CleanMol-extracted QAC/biocide literature plus PubChem BioAssay and ChEMBL 36.
- Safety/selectivity data: Tox21/ToxCast, EPA CompTox, ChEMBL cytotoxicity, and hemolysis/selectivity assays where available.
- Candidate generator: REINVENT 4, guided by a CleanMol-trained scoring profile.
- Property model: Chemprop v2 ensemble plus a simple fingerprint baseline.
- Physics/3D model: FairChem UMA with the `omol` task and OMol25-derived checkpoints. UMA should rank conformers, charge/spin assumptions, and structural plausibility; it should not be treated as the primary antimicrobial activity model.

See `docs/lysol_2_discovery_strategy.md` for the full model/dataset recommendation and `docs/automated_discovery.md` for the one-click Discovery workflow.

## FairChem / UMA Bridge

CleanMol now writes `fairchem_uma_candidates.csv` during the merge/export stage. This file is a review sheet for downstream FairChem UMA modeling: it deduplicates validated SMILES, suggests the `omol` UMA task, records charge/spin hints, and flags molecules that need charge or salt/counterion review before 3D atomistic modeling.

Plain-English path:

1. Run CleanMol first.
2. Open `fairchem_uma_candidates.csv`.
3. Review `readiness_status` and `readiness_notes`.
4. Confirm charge, spin multiplicity, salt/counterion handling, and fragments.
5. Install FairChem separately only if you are ready for atomistic modeling.
6. Use UMA results as one physics review signal, not as proof of antimicrobial activity.

FairChem is optional. It is not required for PDF extraction, dataset building, Discovery Automation, or Excel review packets. On Apple Silicon / M-Series Macs, CleanMol runs normally, but local FairChem/UMA jobs may use CPU unless your local PyTorch/FairChem setup supports the acceleration you have configured.

For generation, use `candidate_generation_seed.smi` instead of the broad `molecules.smi` file. CleanMol also writes `legacy_or_low_priority_molecules.csv` and `screening_score_profile.json`.

The automated Discovery workflow writes:

- `discovery/training_activity_table.csv`
- `discovery/training_toxicity_table.csv`
- `discovery/resolved_generation_seeds.smi`
- `discovery/ranked_lab_candidates.csv`
- `discovery/ranked_lab_candidates_review.xlsx`
- `discovery/discovery_source_manifest.json`
- `discovery/dataset_quality_report.json`

See `docs/fairchem_uma.md` for the FairChem/UMA workflow and the Hugging Face leaderboard submission API notes.

## Quick Start

Open the repository's `setup` folder, then choose the folder for your computer.

```text
setup/
  windows/   Use this on a Windows PC
  mac/       Use this on an Apple Mac
```

Each folder uses the same order:

1. Install
2. Run
3. End when finished

### Windows Installation

1. Install Python 3.10+ and Node.js 20.9+.
2. Open `setup\windows`.
3. Double-click:

```bat
1-install-windows.bat
```

### Windows Run

Double-click:

```bat
2-run-windows.bat
```

Then enter API keys and folder paths in the app.

### Windows Stop

Double-click:

```bat
3-end-windows.bat
```

### Mac Installation

1. Install Python 3.10+ and Node.js 20.9+. On M-Series Macs, Homebrew is usually the easiest path:

```bash
brew install python node
```

2. In Terminal, run from `setup/mac`:

```bash
chmod +x 1-install-mac.command 2-run-mac.command 3-end-mac.command
./1-install-mac.command
```

### Mac Run

```bash
./2-run-mac.command
```

Then open `http://localhost:3000`. If port 3000 is busy, the Mac runner chooses the next open port from 3000 to 3024 and opens it automatically.

### Mac Stop

```bash
./3-end-mac.command
```

## Default Folders

The installer creates:

- Input: `C:\Users\YourName\CleanMol\input`
- Output: `C:\Users\YourName\CleanMol\output`

On Mac, the installer creates:

- Input: `/Users/YourName/CleanMol/input`
- Output: `/Users/YourName/CleanMol/output`

## Manual Setup

Backend:

```powershell
cd <app folder>/backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8787
```

Mac activation uses:

```bash
source .venv/bin/activate
```

Frontend:

```powershell
cd <app folder>/frontend
npm install
npm run dev
```

Then open `http://localhost:3000`.

## Output Structure

```text
output_folder/
  dataset.db
  combined_dataset.xlsx
  unified_dataset.xlsx
  exports/
    doc_xxx_molecules.jsonl
    doc_xxx_experiments.jsonl
    doc_xxx_results.jsonl
    doc_xxx_dataset.jsonl
  bundles/
    doc_xxxxxxxx/
      paper.md
      metadata.json
      provenance.json
      extraction_primary.json
      audit_openai.json
      gaps_gap_hunter.json
      extraction_with_smiles.json
      extraction_validated.json
      doc_xxxxxxxx_review.xlsx
  logs/
  fairchem_uma_candidates.csv
  candidate_generation_seed.smi
  legacy_or_low_priority_molecules.csv
  screening_score_profile.json
  discovery/
    training_activity_table.csv
    training_toxicity_table.csv
    resolved_generation_seeds.smi
    ranked_lab_candidates.csv
    ranked_lab_candidates_review.xlsx
    discovery_source_manifest.json
```

## API Keys

Keys are stored in browser localStorage and sent only to the local backend for provider API calls.

- Anthropic: required for primary extraction and repair
- OpenAI: optional but recommended for audit verification
- Google Gemini: optional but recommended for gap hunting

## References

- Anthropic model overview: https://platform.claude.com/docs/en/about-claude/models/overview
- Anthropic Models API: https://platform.claude.com/docs/en/api/models/list
- OpenAI model overview: https://developers.openai.com/api/docs/models
- OpenAI Models API: https://developers.openai.com/api/reference/resources/models/methods/list
- Gemini 3.1 Pro Preview model page: https://ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview
- Gemini Models API: https://ai.google.dev/api/models#v1beta.models.list
- ChEMBL downloads: https://chembl.gitbook.io/chembl-interface-documentation/downloads
- PubChem resources: https://www.ncbi.nlm.nih.gov/guide/chemicals-bioassays/
- BindingDB info: https://www.bindingdb.org/rwd/bind/info.jsp
- FAIR Chemistry install: https://fair-chem.github.io/install/
- FAIR Chemistry quickstart: https://fair-chem.github.io/quickstart/
- UMA guide: https://fair-chem.github.io/uma/
- UMA model access: https://huggingface.co/facebook/UMA

## License

CleanMol Discovery is source-available under the CleanMol Discovery Research License. It is free for research, education, nonprofit, and individual use. Commercial use requires a separate written commercial license.
