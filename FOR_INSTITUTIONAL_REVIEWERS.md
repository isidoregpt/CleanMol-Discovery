# CleanMol Discovery for Institutional Reviewers

CleanMol Discovery is a source-available public research preview for dataset building, candidate prioritization, and expert review support. It is not a validated antimicrobial discovery engine, product-development tool, synthesis-planning system, or regulatory tool.

## Data Handling

CleanMol runs locally by default. API calls occur only when the user provides provider keys and starts a workflow that requires external LLM or dataset services. API keys are stored in browser localStorage for convenience and can be cleared from the app.

For shared lab machines, users should clear saved keys after each session or use reduced-egress mode.

## Network Egress

Possible outbound calls:

- Anthropic for primary extraction and figure/extraction roles
- OpenAI for audit roles
- Google Gemini for gap-hunt roles
- Hugging Face for optional dataset source search/pull
- optional user-configured external tools

Reduced-egress / local-only mode disables provider LLM calls, Hugging Face/API pulling, and online source search.

## Outputs

Discovery packets include:

- `DISCLAIMER.txt`
- `run_environment.json`
- `discovery_source_manifest.json`
- `dataset_quality_report.json`
- `ranked_hypothesis_candidates.csv`
- `ranked_hypothesis_candidates_review.xlsx`

API keys are not written to packets. Reviewers should still inspect logs and generated output folders before approving use in sensitive environments.

## Scientific Claim Boundary

Candidate rankings are triage scores. They are not probabilities and are not laboratory results. Any real-world follow-up requires qualified expert review and independent testing.
