# Lysol 2.0 Discovery Strategy

CleanMol's highest-value path is not a single model or a single dataset. The right architecture is a staged discovery stack:

1. Build a disinfectant-focused dataset from papers and public bioactivity sources.
2. Train antimicrobial and selectivity predictors on that dataset.
3. Generate new molecules around promising cationic/amphiphilic scaffolds.
4. Rank candidates with activity, toxicity, synthesizability, formulation, and atomistic-feasibility scores.
5. Send only the smallest, best-reviewed candidate set to qualified lab testing.

## Bottom Line Recommendation

Use this stack:

| Role | Best fit | Why |
| --- | --- | --- |
| Literature extraction | CleanMol with `claude-opus-4-7`, `gpt-5.5`, `gemini-3.1-pro-preview` | Turns QAC/biocide papers into evidence-grounded molecule/activity rows. |
| Primary activity dataset | CleanMol-curated QAC/biocide dataset + PubChem BioAssay + ChEMBL 36 | Antimicrobial activity is the actual target. This is where MIC/MBC/log-reduction/selectivity labels should come from. |
| Toxicity/selectivity dataset | Tox21/ToxCast, EPA CompTox, ChEMBL cytotoxicity/hemolysis assays | A better disinfectant must not just be potent; it must have a usable safety and handling profile. |
| Property predictor | Chemprop v2 ensemble plus a fast Morgan-fingerprint baseline | Chemprop is a strong modern molecular property prediction framework; the baseline prevents fooling ourselves on small data. |
| Molecule generator | REINVENT 4 with transfer learning/RL against CleanMol's scoring profile | REINVENT 4 is purpose-built for de novo design, R-group replacement, scaffold hopping, and multi-objective optimization. |
| Physics / 3D scorer | UMA, preferably current UMA small/medium checkpoint with task `omol`, trained with OMol25 | UMA/OMol25 is excellent for atomistic energy/force/conformer/strain checks. It should rank and sanity-check candidates, not be the main antimicrobial activity model. |
| Dataset for UMA physics | OMol25 | The relevant FairChem molecular dataset: wB97M-V/def2-TZVPD, broad molecular diversity, explicit charge/spin metadata. |

## Why UMA Is Useful, But Not Sufficient

UMA is a universal interatomic potential. It helps answer questions like:

- Does this molecule have plausible low-energy conformers?
- Are charge/spin/fragment assumptions reasonable?
- Is the candidate structurally strained or unstable?
- Which conformer should be used for downstream calculations?

UMA does not directly know whether a molecule kills bacteria, whether it disrupts membranes better than benzalkonium chloride, whether it is safe for humans, or whether it works in a real cleaner formulation. Those labels must come from the biological/chemical dataset that CleanMol is built to curate.

For this app, use UMA as a late-stage physics filter and 3D feature generator after the activity/selectivity model has already narrowed the candidate pool.

## Best Dataset Shape

The core training table should be one row per molecule-organism-assay-condition measurement:

```text
smiles
molecule_id
organism
strain
assay_type
endpoint
value
units
exposure_time
formulation_context
serum_or_soil_load
temperature
pH
source_paper
evidence_page
evidence_snippet
```

For early modeling, normalize endpoints into a few prediction targets:

- Gram-positive potency, such as `S. aureus` MIC/MBC/log reduction.
- Gram-negative potency, such as `E. coli` and `P. aeruginosa`.
- Fungal potency, such as `C. albicans`.
- Cytotoxicity/hemolysis/selectivity.
- Resistance/adaptation risk when papers provide repeated-exposure data.
- Formulation viability proxies: solubility, cLogP range, surfactant class, salt/counterion, heavy atom count, charge.

## Recommended Dataset Priority

1. CleanMol-extracted QAC/biocide literature: most important because disinfectant SAR is underrepresented in generic drug datasets.
2. PubChem BioAssay: useful for active/inactive antimicrobial and toxicity labels at scale, with assay provenance.
3. ChEMBL 36: useful for curated bioactivity, cytotoxicity, ADMET-like endpoints, and deduplication by InChIKey.
4. Tox21/ToxCast/CompTox: use as safety screens and liabilities.
5. OMol25: use for UMA physics, conformer, strain, and charge/spin-aware molecular modeling. Do not use it as the primary antimicrobial activity dataset.
6. BindingDB: lower priority for this goal unless you pivot to a specific protein target. Broad disinfectants usually act through membrane/surface disruption, not one binding pocket.

## Model Workflow

### Phase 1: Curate

Use CleanMol to extract molecules, MIC/MBC/log-reduction values, organism/strain, exposure protocol, and exact evidence from disinfectant and QAC papers.

### Phase 2: Predict

Train a Chemprop v2 multitask model:

- Inputs: canonical SMILES plus optional RDKit descriptors.
- Targets: potency buckets/regression, cytotoxicity, hemolysis/selectivity, and resistance/adaptation flags.
- Validation: scaffold split, paper split, and time split if enough data exists.

Also keep a fast baseline:

- Morgan fingerprints + random forest / XGBoost / logistic regression.
- If Chemprop only barely beats this baseline, the dataset is not ready for aggressive generation.

### Phase 3: Generate

Use REINVENT 4:

- Transfer-learn on known active QAC/biocide molecules and CleanMol's best extracted compounds.
- Optimize with a multi-objective score:
  - predicted broad-spectrum potency up
  - predicted cytotoxicity/hemolysis down
  - novelty moderate, not extreme
  - synthetic accessibility acceptable
  - avoid PAINS/reactive/toxicophores
  - maintain formulation-friendly property windows

### Phase 4: Physics Filter

Use UMA/OMol25 task `omol` for candidates that survive QSAR/generation:

- Generate 3D conformers with RDKit or another conformer tool.
- Confirm total charge and spin multiplicity.
- Use UMA to relax/rank conformers and flag high-strain candidates.
- For salts/counterions, explicitly decide whether to model the full salt or active cation/anion.

### Phase 5: Lab Candidate Triage

The app should produce a short review packet, not a giant generated list:

- 20-100 candidate molecules
- predicted activity and uncertainty
- nearest known analogs
- evidence trail to source papers
- reason selected
- safety/liability flags
- formulation notes
- UMA readiness/charge/fragment notes

## What CleanMol Now Enforces

CleanMol now separates extracted molecules into discovery tiers before export:

- `modern_seed`: stable cationic/amphiphilic scaffolds that can seed a generator after chemist review.
- `needs_review`: potentially relevant structures that need counterion, charge, formulation, or evidence review first.
- `legacy_or_low_priority`: neutral single-nitrogen compounds, simple amines, and other weak seed candidates.
- `insufficient_structure`: missing or invalid structures that cannot be used until repaired.

The specific problem this addresses is the old behavior where any molecule with a nitrogen atom could drift into
the generation pool. Neutral single-nitrogen amines and simple monoamines are now penalized and exported as
baseline/reference molecules instead of primary generation seeds.

The merge step now creates:

- `candidate_generation_seed.smi`
- `screening_score_profile.json`
- `legacy_or_low_priority_molecules.csv`

The currently implemented files are `analysis_ready.csv`, `molecules.smi`, `fairchem_uma_candidates.csv`,
`candidate_generation_seed.smi`, `legacy_or_low_priority_molecules.csv`, `screening_score_profile.json`,
`discovery/training_activity_table.csv`, `discovery/training_toxicity_table.csv`,
`discovery/ranked_lab_candidates.csv`, and `discovery/ranked_lab_candidates_review.xlsx`.

The remaining higher-end upgrade is replacing the lightweight nearest-neighbor baseline with a trained Chemprop v2
ensemble and a fully configured REINVENT 4 scoring plugin when those dependencies are installed.

The Dataset Quality Equalizer now makes uploaded and auto-created datasets pass through the same gates. CleanMol can
therefore give both groups the same Discovery experience and the same standard of review, while still being honest
when an auto-created packet is a starter rather than curated-grade evidence.

## Sources

- FAIR Chemistry install: https://fair-chem.github.io/install/
- FAIR Chemistry quickstart: https://fair-chem.github.io/quickstart/
- FAIR Chemistry UMA guide: https://fair-chem.github.io/uma/
- OMol25 dataset docs: https://fair-chem.github.io/omol25
- OMol25 paper: https://arxiv.org/abs/2505.08762
- REINVENT 4 paper: https://jcheminf.biomedcentral.com/articles/10.1186/s13321-024-00812-5
- REINVENT 4 GitHub: https://github.com/MolecularAI/REINVENT4
- Chemprop docs: https://chemprop.readthedocs.io/
- ChEMBL downloads: https://chembl.gitbook.io/chembl-interface-documentation/downloads
- PubChem BioAssay docs: https://pubchem.ncbi.nlm.nih.gov/docs/bioassays
- Tox21 data/tools: https://tox21.gov/data-and-tools/
