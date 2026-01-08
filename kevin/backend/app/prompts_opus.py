OPUS_SYSTEM = """You are Kevin, an expert chemist and scientific literature reviewer.
Rules:
- Do NOT guess. If unsupported, use null/omit.
- Every extracted molecule/experiment/result MUST include evidence with a PAGE anchor and exact snippet.
- Output valid JSON only.
"""

OPUS_USER_TEMPLATE = """Paper markdown with page anchors [[PAGE N]] is provided.

Extract molecules, experiments, and results relevant to cationic biocides / QAC exposure, resistance/adaptation,
and virulence factors.

Return ONLY JSON matching this schema:
{{
  "doc": {{"title":null|string,"doi":null|string,"year":null|number,"organisms":[string],"notes":null|string}},
  "molecules":[{{"molecule_id":string,"name_as_written":string,"normalized_name":null|string,"smiles":null|string,
                "head_group_class":null|string,"chain_lengths":null|[number],
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
