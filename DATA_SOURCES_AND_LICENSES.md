# Data Sources and Licenses

CleanMol records provenance where source information is known, but users remain responsible for checking source licenses, terms, redistribution rights, and commercial-use limits before using any data outside research review.

| Source | URL | Typical use | License or terms | Commercial / redistribution caution |
| --- | --- | --- | --- | --- |
| User-uploaded datasets | local file | private activity and assay rows | user-controlled | user must confirm rights |
| CleanMol PDF extracts | local papers | structured literature extraction | source-paper dependent | do not redistribute copyrighted papers or extracted protected content without rights |
| Hugging Face datasets | https://huggingface.co/datasets | optional public/source search | dataset-specific | verify each dataset card |
| PubChem | https://pubchem.ncbi.nlm.nih.gov | identifiers, bioassay references | public-domain/federal-source style terms vary by component | verify downstream use |
| ChEMBL | https://www.ebi.ac.uk/chembl/ | bioactivity references | ChEMBL terms/license | verify redistribution and commercial use |
| EPA CompTox | https://comptox.epa.gov/dashboard | safety/toxicity references | EPA terms | verify source terms |
| Tox21/ToxCast | public program sources | toxicity signals | source-specific | verify source terms |
| FAIR Chemistry / FairChem | https://fair-chem.github.io/ | optional atomistic review resource | project/model specific | UMA model access and terms may be gated |

Every discovery row should preserve:

- `source_name`
- `source_type`
- `source_url_or_path`
- `retrieval_date`
- `license_or_terms_if_known`
- `provenance_category`
- `experimental_vs_synthetic_vs_heuristic`

If those fields are missing, treat the row as incomplete provenance until reviewed.
