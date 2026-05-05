# CleanMol Discovery Public Review Disclaimer

CleanMol Discovery is being shared for public research review as a dataset-building and candidate-prioritization tool.

It is not proof that any molecule is antimicrobial, safe, synthesizable, stable in a formulation, legally usable, regulatory-ready, or commercially suitable.

## What CleanMol Is For

CleanMol is intended to help researchers:

1. turn chemistry papers, patents, uploaded datasets, and public sources into structured review data
2. keep citations, provenance, and quality gates visible
3. generate and rank candidate molecules for qualified chemist review
4. prepare optional FAIR Chemistry / UMA review files for atomistic plausibility checks
5. compare uploaded, public, and auto-created datasets under the same quality gates

## What CleanMol Is Not

CleanMol is not:

- a clinical, medical, veterinary, regulatory, or consumer-product safety tool
- a guarantee of antimicrobial efficacy
- a toxicity, environmental fate, or human-safety determination
- a synthesis-planning system
- a substitute for a qualified chemist, microbiologist, toxicologist, formulation scientist, regulatory specialist, or laboratory validation
- permission to manufacture, sell, test, or deploy a chemical product

## How To Interpret Candidate Rankings

Candidate rankings are research triage signals. They are meant to answer:

```text
Which candidates should a qualified reviewer inspect first?
```

They do not answer:

```text
Which candidate works in the real world?
Which candidate is safe?
Which candidate should be synthesized?
Which candidate should be used in a product?
```

Any candidate taken beyond software review needs independent expert review, literature review, synthesis feasibility review, toxicology assessment, regulatory review, and laboratory testing.

## Synthetic And Auto-Created Data

CleanMol can auto-create starter datasets and generated candidates when a researcher does not have a private dataset. This is meant to level the starting line, not erase scientific uncertainty.

Synthetic/model-prior rows can help form hypotheses, but they cannot by themselves make a dataset curated-grade. CleanMol labels packets with quality statuses such as `Curated-Grade`, `Strong Starter`, `Useful Starter`, or `Not Ready` so reviewers can see the limits before using the output.

## FAIR Chemistry / UMA

FAIR Chemistry UMA is an optional downstream physics-review path. It can help review atomistic plausibility, conformer strain, charge/spin assumptions, and fragment handling.

UMA does not prove antimicrobial activity, safety, synthesis feasibility, or regulatory readiness.

## Public Review Scope

Public reviewers should focus on:

- whether the workflow is understandable to chemists
- whether provenance and limitations are clear
- whether dataset quality gates are fair and useful
- whether generated candidates are labeled cautiously
- whether the app avoids overstating what software can prove
- whether the outputs are useful enough to guide responsible lab follow-up

## Legal And License Note

CleanMol Discovery is distributed under the CleanMol Discovery Research License. This disclaimer is not legal advice. Before a broad commercial launch, paid deployment, institutional rollout, or public campaign, the license and attribution language should be reviewed by qualified counsel.
