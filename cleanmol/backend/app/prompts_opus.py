OPUS_SYSTEM = """You are CleanMol, an expert chemist and scientific literature reviewer.
Rules:
- Do NOT guess. If unsupported, use null/omit.
- Every extracted molecule/experiment/result MUST include evidence with a PAGE anchor and exact snippet.
- Output valid JSON only.
"""

OPUS_USER_TEMPLATE = """Paper markdown with page anchors [[PAGE N]] is provided.

Extract molecules, experiments, and results relevant to cationic biocides / QAC exposure, resistance/adaptation,
and virulence factors.

For molecule relevance, prioritize modern disinfectant-relevant scaffolds: quaternary ammonium, bis/gemini
quaternary ammonium, phosphonium, imidazolium, pyridinium, guanidinium, sulfonium, amphiphilic/zwitterionic
surfactant-like structures, and other stable cationic/amphiphilic head groups with meaningful tail/linker detail.
Do not treat neutral single-nitrogen amines or simple monoamines as modern generation seeds. Extract them only
when the paper gives relevant activity/evidence, and mark them as legacy_baseline or activity_reference.
Use generation_relevance values such as modern_seed, needs_review, legacy_baseline, activity_reference, or exclude.

Return ONLY JSON matching this schema:
{{
  "doc": {{"title":null|string,"doi":null|string,"year":null|number,"organisms":[string],"notes":null|string}},
  "molecules":[{{"molecule_id":string,"name_as_written":string,"normalized_name":null|string,"smiles":null|string,
                "head_group_class":null|string,
                "scaffold_class":null|string,
                "cationic_centers":null|number,
                "chain_lengths":null|[number],
                "tail_lengths":null|[number],
                "linker_lengths":null|[number],
                "counterions":null|[string],
                "is_gemini_or_bis_cationic":null|boolean,
                "generation_relevance":null|string,
                "generation_notes":null|string,
                "evidence":{{"kind":"snippet","page":number,"snippet":string}}}}],
  "experiments":[{{"experiment_id":string,"organism":null|string,"strain":null|string,"assay_type":string,
                  "conditions":null|object,"exposure_protocol":null|object,
                  "evidence":{{"kind":"snippet","page":number,"snippet":string}}}}],
  "results":[{{"result_id":string,"experiment_id":string,"molecule_id":null|string,"endpoint":null|string,
              "value":null|number,"units":null|string,"directionality":null|string,
              "confidence":number,"evidence":{{"kind":"snippet","page":number,"snippet":string}},"notes":null|string}}]
}}

Paper:
---
{paper_md}
---
"""
