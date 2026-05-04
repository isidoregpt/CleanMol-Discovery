# CleanMol Discovery

CleanMol Discovery is a desktop research application for building chemistry datasets and ranked lab-candidate packets for next-generation disinfectant discovery. It supports Windows and Apple Silicon / M-Series Macs.

The project is designed for the "Lysol 2.0" problem: helping researchers move from scattered papers, patents, public datasets, and incomplete local data toward modern, reviewable candidate molecules that can be evaluated by a chemist and then tested in the lab.

CleanMol is not a replacement for synthesis planning, toxicology, regulatory review, or laboratory validation. It is a dataset-building and candidate-prioritization system meant to make early discovery more accessible, auditable, and modern.

## Who It Is For

- Chemists with papers and PDFs who need structured molecule, assay, and result tables.
- Researchers without a private industrial dataset who need a usable discovery starting point.
- Labs that want uploaded, public, and generated data judged by the same quality gates.
- Review teams that need provenance, citations, exports, and Excel packets instead of opaque model output.

## What CleanMol Does

CleanMol has two main workflows.

### Literature Extraction

The pipeline turns born-digital chemistry PDFs into structured review data:

1. Extract page-anchored markdown from PDFs.
2. Analyze figures for visible structures and SMILES.
3. Extract molecules, experiments, numeric results, and evidence snippets.
4. Audit extracted claims against the source text.
5. Repair weak or rejected claims.
6. Find missed tables, figures, protocols, and results.
7. Enrich molecules with SMILES and RDKit properties.
8. Export SQLite, JSONL, `.smi`, CSV, and Excel review files.

### Discovery Automation

The Discovery Automation panel supports three data paths:

- Upload a chemist-owned CSV or Excel dataset.
- Pull from a curated/searchable online Source Library.
- Auto-create a 2026 starter dataset and candidate packet from CleanMol extracts, public sources, and transparent synthetic/model-prior seeds.

Both uploaded and auto-created datasets pass through the same Dataset Quality Equalizer. CleanMol labels the packet as `Curated-Grade`, `Strong Starter`, `Useful Starter`, or `Not Ready` so a researcher can see whether the dataset is serious enough for downstream modeling.

## Modern Disinfectant Focus

CleanMol does not treat "contains nitrogen" as enough. Simple neutral monoamines and legacy single-nitrogen molecules are retained as baseline or activity-reference records, not as primary generation seeds.

Modern candidate prioritization favors cationic/amphiphilic disinfectant-relevant scaffolds, including:

- quaternary ammonium compounds
- gemini and bis-cationic QACs
- phosphonium and sulfonium motifs
- imidazolium and pyridinium systems
- guanidinium motifs
- zwitterionic surfactant-like structures

Exports include fields such as `modern_disinfectant_score`, `candidate_tier`, `modern_scaffold_tags`, `legacy_flags`, and `generation_recommendation`.

## Recommended Discovery Stack

CleanMol is built around a staged discovery approach:

- Activity modeling: Chemprop v2 multitask ensemble plus a Morgan-fingerprint baseline.
- Generation: REINVENT 4 with a multi-objective CleanMol score profile.
- Physics and 3D review: FairChem UMA with the `omol` task and OMol25-style charge/spin-aware inputs.
- Data foundation: CleanMol-curated QAC/biocide literature plus public bioactivity and safety sources such as PubChem BioAssay, ChEMBL, Tox21/ToxCast, EPA CompTox, and hemolysis/selectivity assays where available.

FairChem UMA is used as a downstream atomistic plausibility and conformer/charge/spin review layer. It is not treated as the primary antimicrobial activity model.

## LLM Model Defaults

CleanMol defaults to the latest provider frontier models when API keys are available. The backend checks provider model-list APIs for Anthropic, OpenAI, and Google model availability, and the frontend has a `Refresh latest` button in the Models panel.

If a key is missing, a provider cannot be reached, or a suitable frontier model cannot be selected, CleanMol falls back to verified model IDs:

| Role | Verified fallback |
| --- | --- |
| Primary extraction and repair | `claude-opus-4-7` |
| Figure analysis | `claude-opus-4-7` |
| Audit | `gpt-5.5` |
| Gap hunt | `gemini-3.1-pro-preview` |

The `Use latest provider models by default` option is enabled by default. Turn it off to run exactly the visible model IDs.

## Key Outputs

Typical extraction outputs:

- `dataset.db`
- `combined_dataset.xlsx`
- `unified_dataset.xlsx`
- `analysis_ready.csv`
- `molecules.smi`
- per-document JSONL exports
- per-document review workbooks and provenance bundles

Discovery and candidate outputs:

- `candidate_generation_seed.smi`
- `legacy_or_low_priority_molecules.csv`
- `screening_score_profile.json`
- `fairchem_uma_candidates.csv`
- `discovery/training_activity_table.csv`
- `discovery/training_toxicity_table.csv`
- `discovery/resolved_generation_seeds.smi`
- `discovery/ranked_lab_candidates.csv`
- `discovery/ranked_lab_candidates_review.xlsx`
- `discovery/discovery_source_manifest.json`
- `discovery/dataset_quality_report.json`

## Quick Start

Use the script for your operating system.

### Windows

```bat
install-windows.bat
```

Run:

```bat
run-windows.bat
```

Then open:

```text
http://localhost:3000
```

Stop:

```bat
stop-windows.bat
```

`end-windows.bat` is also available as a plain-language stop alias.

The installer creates default working folders under:

```text
C:\Users\YourName\CleanMol\input
C:\Users\YourName\CleanMol\output
```

The older `install.bat`, `run.bat`, and `stop.bat` files remain for compatibility, but the `*-windows.bat` names are clearer.

### Apple Silicon / M-Series Mac

Open Terminal in the repository root. If needed, make the scripts executable:

```bash
chmod +x install-mac.command run-mac.command stop-mac.command end-mac.command
```

Install:

```bash
./install-mac.command
```

Run:

```bash
./run-mac.command
```

Stop:

```bash
./stop-mac.command
```

`./end-mac.command` is also available as a plain-language stop alias.

The Mac installer creates default working folders under:

```text
/Users/YourName/CleanMol/input
/Users/YourName/CleanMol/output
```

Mac requirements:

- macOS on Apple Silicon / M-Series hardware
- Python 3.10+
- Node.js 20.9+
- npm

Install Python and Node from their official installers, or with Homebrew:

```bash
brew install python node
```

Place PDF files in the input folder, choose an output folder, add API keys, and run the pipeline or Discovery Automation workflow.

## API Keys

Keys are stored in browser localStorage and sent only to the local backend for provider API calls.

- Anthropic: required for primary extraction and repair.
- OpenAI: optional but recommended for audit verification.
- Google Gemini: optional but recommended for gap hunting.
- Hugging Face: optional for source discovery and gated model/dataset access.

The app can still open without API keys, but online LLM extraction, provider-latest model resolution, and some online data/model paths require relevant keys.

## Manual Development Setup

Backend:

```powershell
cd cleanmol/backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8787
```

On Mac, activate the virtual environment with:

```bash
source cleanmol/backend/.venv/bin/activate
```

Frontend:

```powershell
cd cleanmol/frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Repository Layout

```text
.
  cleanmol/
    backend/        FastAPI pipeline, model resolution, extraction, exports
    frontend/       Next.js desktop-style UI
    docs/           Discovery strategy, automation, and FairChem/UMA notes
  install.bat       Windows installer
  install-windows.bat
  install-mac.command
  run.bat           Starts backend and frontend
  run-windows.bat
  run-mac.command
  stop.bat          Stops local app processes
  stop-windows.bat
  stop-mac.command
  end-windows.bat
  end-mac.command
  LICENSE           CleanMol Discovery Research License
  CITATION.cff      Scholarly citation metadata
```

## Documentation

More detailed notes live in:

- `cleanmol/docs/lysol_2_discovery_strategy.md`
- `cleanmol/docs/automated_discovery.md`
- `cleanmol/docs/fairchem_uma.md`

## License And Credit

CleanMol Discovery is source-available under the CleanMol Discovery Research License.

It is free for research, education, nonprofit, and individual use. Commercial use requires a separate written commercial license, including resale, hosted services, private-label distribution, for-profit internal R&D, paid discovery services, product development, and commercialization of outputs or discoveries materially enabled by the software.

Publications, patent filings, datasets, candidate disclosures, regulatory filings, product materials, discovery announcements, and other research or commercial outputs that materially use CleanMol Discovery or its generated outputs must credit:

```text
CleanMol Discovery by Jonathan Graziola
https://github.com/isidoregpt/CleanMol-Discovery
```

For scholarly work, cite the project using `CITATION.cff`. The CleanMol Discovery and CleanMol names are not licensed for misleading resale, endorsement, or branding of forks. See `LICENSE`, `NOTICE`, and `TRADEMARKS.md`.
