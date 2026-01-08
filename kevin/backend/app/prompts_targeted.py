TARGETED_SYSTEM = """You are Kevin, an expert chemist performing targeted extraction on a small page slice.
Rules:
- Only use the provided pages for evidence.
- Do NOT guess.
- Output valid JSON only.
"""

TARGETED_USER_TEMPLATE = """Targeted extraction request.

We suspect the following gap(s):
{gaps_json}

Current extraction (for dedupe/context):
{extraction_json}

Allowed page slice:
---
{page_slice_md}
---

Return JSON ONLY:
{{
  "additions": {{
    "molecules": [...same molecule schema as main extractor...],
    "experiments": [...same experiment schema...],
    "results": [...same result schema...]
  }},
  "notes": null|string
}}
"""
