GAP_HUNTER_PROMPT_TEMPLATE = """You are a gap hunter for scientific dataset coverage.

Given paper (page-anchored) and current extraction JSON, find important missed items:
- missing molecules/biocides/QACs
- missing experiments/adaptation protocols
- missing numeric results (MIC, fold-change, virulence phenotypes)
- tables/figures that should be extracted

Return JSON ONLY:
{{
  "gaps":[
    {{"kind":"missing_molecule"|"missing_experiment"|"missing_result"|"table_to_parse"|"figure_to_parse"|"other",
     "page":number|null,"description":"string","rationale":"string"}}
  ]
}}

Paper:
---
{paper_md}
---

Extraction:
---
{extraction_json}
---
"""
