REPAIR_SYSTEM = """You are CleanMol, an expert chemist and scientific extraction repair agent.
Rules:
- Do NOT guess.
- Evidence snippet MUST appear verbatim in provided slice pages.
- Output valid JSON only.
"""

REPAIR_USER_TEMPLATE = """Repair ONE entity using ONLY the provided page slice.

Entity type: {entity_type}
Current entity JSON:
{entity_json}

Audit verdict: {verdict}
Audit issues:
{issues_json}

Allowed page slice:
---
{page_slice_md}
---

Return JSON ONLY:
{{
  "repaired_entity": {{ ... }},
  "repair_notes": null|string
}}
"""
