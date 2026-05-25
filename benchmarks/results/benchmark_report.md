# Benchmark Report

Status: sanity check completed in a CleanMol Core environment with RDKit installed.

RDKit version: `2026.03.2`

Valid or expected-invalid rows checked: 11

Valid benchmark structures: 10

Morgan baseline reference rows: 10

Ranking sanity check: passed

Unexpected failures: none

| Name | Expected group | Valid | Candidate tier | Rank score | Morgan neighbors | Nearest similarity | Score provenance |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| benzalkonium_chloride_like | qac | yes | modern_seed | 69.5 | 7 | 1.0 | rdkit_morgan_fingerprint_baseline_plus_discovery_profile |
| cetylpyridinium_chloride_like | pyridinium | yes | modern_seed | 70.16 | 7 | 1.0 | rdkit_morgan_fingerprint_baseline_plus_discovery_profile |
| chlorhexidine_like | bis_cationic_control | yes | needs_review | 47.17 | 1 | 1.0 | rdkit_morgan_fingerprint_baseline_plus_discovery_profile |
| phosphonium_c12 | phosphonium | yes | modern_seed | 68.33 | 7 | 1.0 | rdkit_morgan_fingerprint_baseline_plus_discovery_profile |
| pyridinium_c12 | pyridinium | yes | modern_seed | 70.16 | 7 | 1.0 | rdkit_morgan_fingerprint_baseline_plus_discovery_profile |
| gemini_bis_qac | gemini_qac | yes | modern_seed | 73.7 | 7 | 1.0 | rdkit_morgan_fingerprint_baseline_plus_discovery_profile |
| simple_monoamine | lower_priority_control | yes | legacy_or_low_priority | 32.55 | 7 | 1.0 | rdkit_morgan_fingerprint_baseline_plus_discovery_profile |
| neutral_hydrocarbon | negative_control | yes | legacy_or_low_priority | 34.23 | 7 | 1.0 | rdkit_morgan_fingerprint_baseline_plus_discovery_profile |
| invalid_smiles | invalid | no | reject |  |  |  | invalid_smiles_rejected |
| salt_counterion | salt_counterion | yes | modern_seed | 64.8 | 7 | 1.0 | rdkit_morgan_fingerprint_baseline_plus_discovery_profile |
| long_chain_cationic_toxicity_risk | toxicity_risk_review | yes | modern_seed | 64.8 | 7 | 1.0 | rdkit_morgan_fingerprint_baseline_plus_discovery_profile |

This report is not a validation claim.
