# FAIR Chemistry / FairChem UMA Guide

This page is for chemists who see `fairchem_uma_candidates.csv` and wonder what to do with it.

Short version: CleanMol prepares candidates for FAIR Chemistry review. FAIR Chemistry UMA is optional. You do not need it to extract papers, build datasets, auto-create candidates, or open the Excel review packet.

## Where FairChem Fits

CleanMol answers:

1. What molecules, experiments, and results are in my papers?
2. Which public or uploaded data can support a disinfectant discovery dataset?
3. Which generated candidates deserve chemist review?
4. Which candidates have valid SMILES, charge hints, fragment counts, and review notes?

FairChem UMA helps later with:

1. atomistic structure sanity checks
2. conformer and strain review
3. charge and spin-aware molecule modeling
4. molecular dynamics or energy-style review through ASE

It does not tell you whether a molecule is safe, disinfectant-active, easy to synthesize, or acceptable for a cleaning product. Those questions still need biological data, formulation science, toxicology, and lab testing.

## The CleanMol File To Use

CleanMol writes:

```text
fairchem_uma_candidates.csv
```

This is the handoff file for FairChem/UMA. It includes:

- `smiles`
- `uma_task`
- `total_charge_hint`
- `spin_multiplicity_hint`
- `fragment_count`
- `atom_count`
- `readiness_status`
- `readiness_notes`

For CleanMol's disinfectant work, the suggested UMA task is usually:

```text
omol
```

The official FairChem quickstart describes `omol` as the molecules and polymers task.

## Readiness Status

Use this as a plain-English checklist:

- `candidate`: reasonable starting point for RDKit 3D conformer generation and UMA review.
- `needs_structure_review`: rerun or inspect RDKit validation before UMA.
- `needs_charge_review`: confirm total charge, counterion handling, and spin multiplicity.
- `needs_fragment_review`: decide whether to model the full salt/counterion system or only the active fragment.
- `invalid_smiles` or `missing_smiles`: not ready for FairChem.

If you are not sure what charge, spin, or counterion to use, stop and ask a computational chemist before running UMA.

## Optional FairChem Install

Do this only if you actually want to run local FairChem/UMA modeling. It is not part of the basic CleanMol install.

The official FairChem docs recommend installing in a virtual environment. They also note that FairChem V2 is a breaking change from V1 and is not compatible with older pretrained models.

### Step 1: Create A Separate Environment

Use a separate environment so FairChem does not disturb the CleanMol app environment.

```bash
python3 -m venv fairchem
source fairchem/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv fairchem
.\fairchem\Scripts\activate
```

The official FairChem example uses Python 3.12. If your computer has several Python versions installed, choose the Python 3.12 executable for this separate environment.

### Step 2: Install FairChem Core

```bash
pip install fairchem-core
```

FairChem V2 removed several third-party dependencies that previously made installation difficult, so the core install is simpler than older FairChem releases.

### Step 3: Request UMA Access

UMA checkpoints are gated on Hugging Face.

1. Create or sign in to a Hugging Face account.
2. Request access to `facebook/UMA`.
3. Create a Hugging Face token with read access for gated repositories.
4. Log in with the Hugging Face CLI or set `HF_TOKEN`.

```bash
huggingface-cli login
```

or:

```bash
export HF_TOKEN=your_token_here
```

On Windows PowerShell:

```powershell
$env:HF_TOKEN="your_token_here"
```

## First UMA Run Concept

The official quickstart uses ASE and `FAIRChemCalculator`. For molecule work, the concept is:

```python
from ase.build import molecule
from fairchem.core import pretrained_mlip, FAIRChemCalculator

predictor = pretrained_mlip.get_predict_unit("uma-s-1p2", device="cuda")
calc = FAIRChemCalculator(predictor, task_name="omol")

atoms = molecule("H2O")
atoms.info.update({"charge": 0, "spin": 1})
atoms.calc = calc
energy = atoms.get_potential_energy()
```

On an M-Series Mac, start without `device="cuda"` or use `device="cpu"` unless you have confirmed a supported accelerator path. CPU is slower, but it is a simpler first test. Larger UMA batches are better suited to a CUDA workstation or cloud GPU.

CleanMol does not automatically run this today because a responsible UMA run requires a reviewed 3D structure, charge, spin, salt/counterion decision, and hardware choice.

## How This Helps Lysol 2.0 Discovery

Use FairChem/UMA after CleanMol has narrowed the field.

Recommended order:

1. Use CleanMol to extract and build the dataset.
2. Use Discovery Automation to rank candidates.
3. Review `ranked_lab_candidates_review.xlsx`.
4. Check `fairchem_uma_candidates.csv`.
5. Promote only reviewed candidates to FairChem/UMA.
6. Use UMA results as one review signal, not as proof of biological activity.

## Leaderboard Note

Do not auto-submit CleanMol outputs to the FairChem leaderboard. The leaderboard is for benchmark prediction files from a model evaluation run, not literature-extracted molecule tables or early discovery candidates.

If you ever do submit to the leaderboard, fetch the live Gradio config at submission time because dependency IDs can change.

## Official Resources

- FairChem install: https://fair-chem.github.io/install/
- FairChem quickstart: https://fair-chem.github.io/quickstart/
- UMA guide: https://fair-chem.github.io/uma/
- UMA model access: https://huggingface.co/facebook/UMA
- FairChem leaderboard: https://huggingface.co/spaces/facebook/fairchem_leaderboard
