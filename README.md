# CleanMol Discovery

CleanMol Discovery is an early-stage research tool for building structured chemistry datasets and producing ranked disinfectant-relevant hypothesis packets for qualified chemist review. It supports Windows and Apple Silicon / M-Series Macs.

The project is designed for the "Lysol 2.0" problem: helping researchers move from scattered papers, patents, public datasets, and incomplete local data toward modern, reviewable candidate molecules that can be evaluated by a chemist and then tested in the lab.

CleanMol Discovery is an early-stage research triage tool.

It helps organize chemistry data, generate disinfectant-relevant molecular hypotheses, and prioritize candidates for expert review.

It does not prove antimicrobial activity, safety, synthesizability, formulation stability, environmental acceptability, regulatory compliance, or commercial suitability.

Candidate rankings are not probabilities and are not laboratory results.

Any candidate considered for real-world follow-up requires independent review by qualified chemists, microbiologists, toxicologists, formulation scientists, regulatory experts, and laboratory testing.

## Public Review Preview

CleanMol Discovery is ready for public review as an early research preview. Reviewers should start here:

- `PUBLIC_REVIEW_DISCLAIMER.md`: what CleanMol can and cannot claim
- `SECURITY.md`: information security review notes for CISOs and institutional approvers
- `cleanmol/docs/start_here_public_review.md`: one-page reviewer guide
- `samples/public_review_demo/`: small synthetic demo output packet

The demo packet is intentionally synthetic and labeled `Not Ready`. It exists to show output shape, file meaning, quality gates, and FAIR Chemistry / UMA readiness notes without requiring API keys, private papers, or a long model run.

## Implementation Status

| Capability | Current status | Default install? | Notes |
| --- | --- | --- | --- |
| PDF text extraction | Implemented | Yes | Born-digital PDFs preferred |
| LLM extraction | Implemented | Yes | Requires provider API key |
| Figure analysis | Experimental | Yes | Needs validation against benchmark set |
| SMILES validation | Implemented | Yes | RDKit-based |
| RDKit Morgan baseline | Implemented | Yes | Default similarity baseline |
| Candidate ranking | Implemented | Yes | Triage score, not probability |
| Built-in candidate generator | Implemented | Yes | Rule-based hypothesis generator |
| Chemprop v2 | Optional advanced | No | Install through Advanced Discovery Pack |
| REINVENT 4 | Optional advanced/manual | No | Requires external config |
| FairChem/UMA | Handoff only | No | Optional expert review path |
| Lab validation | Not included | No | External requirement |

## Install Tiers

CleanMol Core is the default installation. It includes the backend, frontend, RDKit, PDF extraction, LLM extraction pipeline, SMILES validation, CSV/XLSX export, Excel review workbooks, Dataset Quality Equalizer, built-in rule-based hypothesis generation, RDKit Morgan fingerprint baseline, heuristic scoring fallback, demo mode, provenance, and run metadata.

The Advanced Discovery Pack is optional. It can help configure Chemprop v2 and REINVENT 4 in a separate advanced environment, but a failed advanced setup does not break CleanMol Core.

FairChem/UMA is treated as an expert/manual handoff. CleanMol prepares `fairchem_uma_candidates.csv`, charge/spin hints, fragment warnings, and readiness notes. CleanMol does not run UMA by default and does not use UMA as proof of antimicrobial activity.

## Start Here

- `FOR_CHEMISTS.md`: plain-English setup, first run, demo, and output guide.
- `FOR_COMPUTATIONAL_CHEMISTS.md`: optional advanced integrations and scoring notes.
- `FOR_INSTITUTIONAL_REVIEWERS.md`: review posture, security, privacy, and deployment considerations.
- `VALIDATION_STATUS.md`: what is implemented, benchmarked, experimental, or not validated.
- `DATA_SOURCES_AND_LICENSES.md`: source provenance and licensing cautions.
- `SYSTEM_REQUIREMENTS.md`: supported platforms and practical sizing guidance.
- `TROUBLESHOOTING.md`: common install, API, PDF, Excel, and port issues.
- `RELEASE_CHECKLIST.md`: public-preview readiness checklist.

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

## How To Use CleanMol Without Getting Lost

Use this section as the simple map.

### If You Have PDFs

1. Put PDFs in the input folder.
2. Choose an output folder.
3. Add an Anthropic key.
4. Click `Run Pipeline`.
5. Review the Excel workbook and CSV outputs.

This path turns papers and patents into structured chemistry data.

### If You Have Your Own Dataset

1. Choose an output folder.
2. Open `Discovery Automation`.
3. Select `Chemist upload`.
4. Upload CSV or Excel data.
5. Click `Run Discovery`.
6. Review `ranked_lab_candidates_review.xlsx`.

This path lets a chemist use private data while still getting the same CleanMol quality gates.

### If You Do Not Have A Dataset

1. Choose an output folder.
2. Open `Discovery Automation`.
3. Select `Auto-create`.
4. Keep public sources enabled.
5. Click `Run Discovery`.
6. Review `dataset_quality_report.json` before trusting any ranking.

This path builds a usable starter packet from CleanMol extracts, curated public sources, Hugging Face/API search, and transparent generated seeds.

### If You Want FairChem / UMA Review

1. Run the pipeline or Discovery Automation first.
2. Open `fairchem_uma_candidates.csv`.
3. Review charge, spin, fragments, and readiness notes.
4. Install FairChem separately only if you are ready to run atomistic modeling.
5. Treat UMA output as a physics review signal, not as proof of antimicrobial activity.

This path is optional. CleanMol does not require FairChem for normal dataset building or candidate ranking.

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

## Optional Advanced Discovery Stack

CleanMol can support a staged discovery approach when optional tools are installed:

- Activity modeling: Chemprop v2 multitask ensemble plus a Morgan-fingerprint baseline.
- Generation: REINVENT 4 with a multi-objective CleanMol score profile.
- Physics and 3D review: FairChem UMA with the `omol` task and OMol25-style charge/spin-aware inputs.
- Data foundation: CleanMol-curated QAC/biocide literature plus public bioactivity and safety sources such as PubChem BioAssay, ChEMBL, Tox21/ToxCast, EPA CompTox, and hemolysis/selectivity assays where available.

FairChem UMA is used as a downstream atomistic plausibility and conformer/charge/spin review layer. It is not treated as the primary antimicrobial activity model.

## FAIR Chemistry / FairChem Resource

CleanMol incorporates FAIR Chemistry as an optional downstream resource through the Source Library and the `fairchem_uma_candidates.csv` handoff file.

What CleanMol prepares for FairChem:

- `fairchem_uma_candidates.csv`
- suggested UMA task: `omol`
- charge and spin hints
- fragment and salt/counterion review flags
- invalid or missing SMILES warnings
- readiness notes for chemist or computational-chemist review

What FairChem can add later:

- atomistic plausibility review
- conformer and strain checks
- charge and spin-aware molecule modeling
- molecular dynamics or energy-style review through ASE

Optional FairChem setup, in plain English:

1. Finish a CleanMol run first.
2. Ask whether you actually need atomistic modeling yet.
3. If yes, create a separate FairChem virtual environment.
4. Install `fairchem-core`.
5. Request gated access to `facebook/UMA` on Hugging Face.
6. Use `fairchem_uma_candidates.csv` as the checklist before preparing 3D structures.

FairChem is powerful, but it is not a one-click disinfectant predictor. It should not decide whether a molecule is antimicrobial, safe, synthesizable, or commercially usable. CleanMol keeps it separate so non-technical users can still complete the main discovery workflow without fighting a specialized atomistic ML install.

Apple Silicon note: CleanMol installs and runs on M-Series Macs. Local FairChem/UMA review may run on CPU unless the local PyTorch/FairChem stack supports the hardware acceleration you have configured, so larger UMA batches are better suited to a CUDA workstation or cloud GPU.

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
- `discovery/ranked_hypothesis_candidates.csv`
- `discovery/ranked_hypothesis_candidates_review.xlsx`
- `discovery/DISCLAIMER.txt`
- `discovery/run_environment.json`
- `discovery/discovery_source_manifest.json`
- `discovery/dataset_quality_report.json`

What those files help answer:

- `ranked_lab_candidates.csv`: Which molecules should a chemist review first?
- `ranked_lab_candidates_review.xlsx`: What evidence, scores, and warnings support each candidate?
- `dataset_quality_report.json`: Is this dataset strong enough to trust as more than a baseline?
- `discovery_source_manifest.json`: Where did the data come from?
- `candidate_generation_seed.smi`: Which molecules are suitable seeds for de novo generation?
- `legacy_or_low_priority_molecules.csv`: Which molecules were retained for reference but not favored as modern leads?
- `screening_score_profile.json`: How CleanMol weighted activity, toxicity, novelty, scaffold relevance, and review penalties.
- `fairchem_uma_candidates.csv`: Which candidates are ready, or not ready, for optional FAIR Chemistry UMA review?

## Quick Start

Open the `setup` folder, then choose the folder for your computer.

```text
setup/
  windows/   Use this on a Windows PC
  mac/       Use this on an Apple Mac
```

Each operating-system folder uses the same simple order:

1. Install CleanMol
2. Run CleanMol
3. End CleanMol when finished

If you are helping a non-technical reviewer, the plain instruction is:

```text
Open setup.
Open windows or mac.
Click 1 to install.
Click 2 to run.
Click 3 when done.
```

### Windows

Open:

```text
setup\windows
```

Install:

```bat
1-install-windows.bat
```

Run:

```bat
2-run-windows.bat
```

The app opens in the browser. If needed, open:

```text
http://localhost:3000
```

End / stop:

```bat
3-end-windows.bat
```

The installer creates default working folders under:

```text
C:\Users\YourName\CleanMol\input
C:\Users\YourName\CleanMol\output
```

### Apple Silicon / M-Series Mac

Open Terminal in:

```text
setup/mac
```

If needed, make the scripts executable:

```bash
chmod +x 1-install-mac.command 2-run-mac.command 3-end-mac.command
```

Install:

```bash
./1-install-mac.command
```

Run:

```bash
./2-run-mac.command
```

End / stop:

```bash
./3-end-mac.command
```

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

## Information Security

CleanMol is a local research application, not a hardened enterprise multi-user service. It starts local servers, stores API keys in browser `localStorage`, writes local output files, and may send selected document content or derived chemistry data to third-party providers when users enable those workflows.

CISOs and institutional reviewers should read `SECURITY.md` before approval. That file documents local ports, CORS behavior, credential handling, output retention, external services, dependency supply-chain notes, reduced-egress options, and recommended approval controls.

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
  samples/
    public_review_demo/
                    Synthetic sample output packet for public reviewers
  setup/
    README.md       Which setup folder to use
    windows/
      1-install-windows.bat
      2-run-windows.bat
      3-end-windows.bat
    mac/
      1-install-mac.command
      2-run-mac.command
      3-end-mac.command
  LICENSE           CleanMol Discovery Research License
  CITATION.cff      Scholarly citation metadata
```

## Documentation

More detailed notes live in:

- `PUBLIC_REVIEW_DISCLAIMER.md`
- `SECURITY.md`
- `cleanmol/docs/start_here_public_review.md`
- `cleanmol/docs/lysol_2_discovery_strategy.md`
- `cleanmol/docs/automated_discovery.md`
- `cleanmol/docs/fairchem_uma.md`

Sample outputs:

- `samples/public_review_demo/`

Helpful external resources:

- FAIR Chemistry install: https://fair-chem.github.io/install/
- FAIR Chemistry quickstart: https://fair-chem.github.io/quickstart/
- UMA guide: https://fair-chem.github.io/uma/
- UMA model access: https://huggingface.co/facebook/UMA

## License And Credit

CleanMol Discovery is source-available under the CleanMol Discovery Research License.

It is free for research, education, nonprofit, and individual use. Commercial use requires a separate written commercial license, including resale, hosted services, private-label distribution, for-profit internal R&D, paid discovery services, product development, and commercialization of outputs or discoveries materially enabled by the software.

Publications, patent filings, datasets, candidate disclosures, regulatory filings, product materials, discovery announcements, and other research or commercial outputs that materially use CleanMol Discovery or its generated outputs must credit:

```text
CleanMol Discovery by Jonathan Graziola
https://github.com/isidoregpt/CleanMol-Discovery
```

For scholarly work, cite the project using `CITATION.cff`. The CleanMol Discovery and CleanMol names are not licensed for misleading resale, endorsement, or branding of forks. See `LICENSE`, `NOTICE`, and `TRADEMARKS.md`.
