# CleanMol Discovery Information Security Review

This document is written for CISOs, security architects, IT reviewers, privacy teams, research-computing groups, and institutional approvers evaluating CleanMol Discovery for use.

CleanMol Discovery is a local research application for chemistry dataset building, candidate prioritization, and review packet generation. It is not a hosted SaaS platform, not a hardened enterprise multi-user service, and not a regulated production system.

## Executive Security Summary

CleanMol is intended to run on a trusted local workstation controlled by the researcher or institution.

Default operation:

- starts a local FastAPI backend on `127.0.0.1:8787`
- starts a local Next.js frontend on `localhost:3000` or the next open port through `3024`
- reads user-selected local input folders
- writes user-selected local output folders
- stores API keys in the browser's `localStorage`
- sends selected document content, extracted text, figure content, chemical names, candidate data, and prompts to third-party APIs only when the user enables the corresponding workflow and provides API keys
- downloads dependencies from PyPI and npm during install

CleanMol does not intentionally include telemetry, analytics, background cloud sync, hidden account creation, or automatic leaderboard submission.

Important approval point:

CleanMol can process sensitive research documents. If a user enters LLM or dataset-provider API keys, CleanMol may transmit portions of those documents and derived outputs to external providers. CISO review should focus on data classification, vendor approval, egress controls, credential handling, endpoint hardening, and output retention.

## Intended Deployment Model

Approved/expected model:

- single-user local workstation
- institution-managed laptop or desktop
- local browser pointed at `localhost`
- local backend bound to `127.0.0.1`
- encrypted disk recommended
- endpoint protection recommended
- organizational firewall/egress controls recommended

Not approved by default:

- public internet hosting
- shared multi-user server
- cloud deployment reachable by other users
- deployment behind a public URL
- use as a regulated production system
- use with classified, export-controlled, patient-identifiable, or contract-restricted data unless separately approved

If an organization wants to host CleanMol centrally, it should first add authentication, authorization, audit logging, TLS, hardened CORS, role-based access, secrets management, tenant isolation, rate limiting, file scanning, and a formal deployment threat model.

## What The Software Does

CleanMol supports these workflows:

1. Literature extraction from born-digital chemistry PDFs
2. Figure analysis for visible structures and chemical information
3. LLM-assisted extraction of molecules, experiments, results, evidence, and gaps
4. Audit and repair of extracted claims
5. SMILES lookup and validation through public chemistry services and RDKit
6. Dataset export to SQLite, CSV, JSONL, SMI, and Excel-style review files
7. Discovery Automation using uploaded data, public sources, and generated starter candidates
8. Optional FAIR Chemistry / UMA readiness handoff files

CleanMol is not:

- a safety-certified system
- a medical device
- a regulatory submission system
- a synthesis execution system
- a laboratory automation controller
- a secure document vault
- a secrets manager
- a multi-user enterprise application

## Architecture Overview

Local components:

- Frontend: Next.js app in `cleanmol/frontend`
- Backend: FastAPI app in `cleanmol/backend`
- Backend runtime: Python virtual environment at `cleanmol/backend/.venv`
- Frontend runtime: Node dependencies at `cleanmol/frontend/node_modules`
- Runtime logs: `.cleanmol-runtime/`
- User inputs: selected local folders and uploaded local datasets
- User outputs: selected local output folder

Default ports:

- Backend: `http://127.0.0.1:8787`
- Frontend: `http://localhost:3000`, or first available port from `3000` to `3024`

The setup scripts are located in:

```text
setup/windows/
setup/mac/
```

The numbered user flow is:

```text
1-install
2-run
3-end
```

## Local Network Exposure

The provided run scripts start the backend with:

```text
uvicorn app.main:app --host 127.0.0.1 --port 8787
```

This binds the backend to loopback by default.

The frontend is a local Next.js development server. It prints a `localhost` address and may also display a network address depending on the local Next.js runtime and network interfaces. Organizations should use local firewall policy to block inbound access if the machine is on an untrusted network.

Security implications:

- CleanMol has no built-in user login.
- CleanMol has no role-based access control.
- CleanMol has no built-in TLS because it is intended for localhost use.
- CleanMol should not be exposed to a LAN, VPN, or the internet without additional controls.
- If another user can access the same running local web service, that user may be able to operate it.

## CORS Behavior

The backend currently allows local browser origins:

```text
http://localhost:3000
http://127.0.0.1:3000
http://localhost:<any port>
http://127.0.0.1:<any port>
```

This is designed for local development-style operation where the frontend may choose ports `3000` through `3024`.

CISO note:

Any page served from `localhost` or `127.0.0.1` may be able to call the backend while it is running. CleanMol's browser-stored keys are origin-scoped and should not be readable by a different localhost origin, but the backend itself has no authentication. Do not run untrusted local web applications at the same time as CleanMol. For enterprise deployment, restrict CORS to the exact frontend origin and add authentication.

## Authentication And Authorization

CleanMol does not include:

- application login
- SSO
- MFA
- RBAC
- session management
- server-side user accounts
- multi-user authorization boundaries

This is acceptable only for the intended single-user local workstation model.

If an institution needs shared use, add authentication and authorization before approval.

## Credential Handling

API keys are entered in the local browser UI.

Current browser storage keys:

```text
cleanmol:key:openai
cleanmol:key:anthropic
cleanmol:key:gemini
cleanmol:key:hf
cleanmol:models
cleanmol:models:autoLatest
cleanmol:paths
```

Storage behavior:

- Keys are stored in browser `localStorage`.
- Browser `localStorage` is not encrypted by CleanMol.
- Keys are sent from the frontend to the local backend over `http://localhost`.
- The backend uses keys to make HTTPS requests to selected third-party APIs.
- CleanMol is designed to mask API keys in generated run logs.
- The `3-end` scripts stop local servers but do not clear browser `localStorage`.

Risks:

- Browser extensions with page access may be able to inspect local app content.
- A local user with access to the same browser profile may be able to access stored keys.
- Endpoint compromise may expose keys.
- Copying browser profiles may copy stored keys.

Recommended controls:

- Use dedicated API keys for CleanMol.
- Use least-privilege keys where providers support scoped permissions.
- Rotate keys regularly.
- Do not use personal production keys for institutional review.
- Clear browser site data after use on shared machines.
- Prefer an institution-managed browser profile with approved extensions only.
- Use endpoint encryption and endpoint detection controls.
- For enterprise hardening, replace browser `localStorage` with OS keychain, environment variables, or an approved secrets broker.

## External Services And Data Egress

CleanMol sends data externally only when the relevant feature is used and the user has provided the required key or enabled the public-source workflow.

### Install-Time Egress

The setup scripts install dependencies from:

- Python package index through `pip`
- npm registry through `npm install`
- optional Homebrew or official installers if the user installs Python/Node on Mac

Security review considerations:

- `cleanmol/frontend/package-lock.json` pins npm dependency integrity hashes.
- `cleanmol/backend/requirements.txt` pins several Python dependencies exactly and uses range constraints for some provider SDKs.
- Organizations that require fully pinned dependencies should freeze Python transitive dependencies before approval.
- Organizations that require supply-chain attestation should generate an SBOM and scan dependencies before use.

Suggested commands for institutional review:

```bash
npm audit
python -m pip list
python -m pip-audit
```

If using enterprise mirrors, configure `pip` and `npm` to use approved internal registries.

### Runtime Egress

Potential runtime destinations include:

| Destination | Purpose | Data that may be sent |
| --- | --- | --- |
| Anthropic API | primary extraction, repair, figure analysis | paper text, prompts, extracted context, figure/image-derived content |
| OpenAI API | audit verification | extracted claims, source snippets, prompts |
| Google Gemini API | gap hunting | paper text, extracted context, prompts |
| Hugging Face APIs | dataset search, dataset rows, optional gated resources | dataset search queries, selected dataset IDs, optional Hugging Face token |
| ChEMBL API | public activity rows | topical query parameters and public activity fetches |
| PubChem PUG-REST | SMILES lookup | chemical names being looked up |
| NCI/CADD CIR | SMILES lookup fallback | chemical names being looked up |
| OPSIN | SMILES lookup fallback | chemical names being looked up |
| FAIR Chemistry / Hugging Face UMA | optional local model access | token/model access metadata if the user installs and authenticates separately |
| Google Fonts | frontend build/dev font fetch through Next.js font tooling | font request metadata, not research files |

Provider retention, training, logging, and privacy behavior are governed by the user's account settings and the provider's terms. CleanMol does not control third-party provider retention.

Recommended CISO decision:

Do not approve use with confidential, export-controlled, regulated, unpublished, patent-sensitive, or contract-restricted documents until each external provider and data path is approved for that data classification.

## Offline Or Reduced-Egress Use

CleanMol can be opened without API keys, but core LLM extraction requires provider keys.

Reduced-egress options:

- review the included demo packet at `samples/public_review_demo/`
- use uploaded/local datasets without running online LLM extraction
- disable public source pulls in Discovery Automation
- do not enter LLM provider keys
- block outbound egress at the firewall
- use only local output review files

Limitations of reduced-egress mode:

- PDF extraction and LLM-assisted literature extraction will not fully operate without provider keys.
- Provider-latest model resolution cannot run without provider model-list access.
- Public dataset search and pulls will be unavailable if egress is blocked.

## Data Stored Locally

CleanMol writes output files to the user-selected output directory.

Typical outputs include:

- `dataset.db`
- `combined_dataset.xlsx`
- `unified_dataset.xlsx`
- `analysis_ready.csv`
- `molecules.smi`
- per-document JSONL exports
- page-anchored markdown
- extracted model outputs
- provenance bundles
- pipeline logs
- discovery CSV/JSON files
- ranked candidate review packets
- uploaded dataset copies under `discovery_uploads/`

Important:

These files can contain sensitive source text, paper excerpts, molecule names, assay details, extracted claims, model responses, generated candidates, and review notes. Treat the entire output folder as sensitive research data.

CleanMol does not encrypt output files.

Recommended controls:

- Use full-disk encryption.
- Store outputs in approved research storage.
- Apply backup and retention rules.
- Do not sync outputs to unapproved consumer cloud drives.
- Delete output folders when no longer needed.
- Review output files before sharing with third parties.

## Uploaded Dataset Handling

Discovery upload accepts CSV, TSV, XLSX, and XLSM-style files through the local browser UI.

The backend saves uploaded files under:

```text
<output folder>/discovery_uploads/
```

The uploaded filename is sanitized to remove unsafe characters.

Risk notes:

- The backend writes to the user-selected output directory.
- The application is not a malware scanner.
- Uploaded spreadsheet files should be treated as untrusted until reviewed.
- Macro-enabled files should be handled according to institutional spreadsheet policy.

## PDF Handling

CleanMol uses Python PDF tooling, including PyMuPDF, to process PDFs.

Risk notes:

- Malformed PDFs can exercise parser attack surface.
- PDFs may contain sensitive text, figures, embedded metadata, or hidden content.
- Extracted markdown and derived content may be written to output bundles.
- If LLM workflows are enabled, extracted PDF content may be transmitted to external providers.

Recommended controls:

- Process PDFs only from trusted sources.
- Run CleanMol on an institution-managed endpoint.
- Keep dependencies patched.
- Use endpoint protection and document-scanning controls where required.

## Logging

CleanMol logs pipeline progress, run configuration, stage results, warnings, and output paths.

API keys are designed to be masked in generated run logs. However, logs may still include:

- document names
- file paths
- molecule names
- extraction warnings
- source snippets or context summaries
- provider error messages
- output locations

Treat logs as sensitive research artifacts.

Do not paste logs into public issues or third-party tools unless approved.

## Source Code And Secret Hygiene

The repository should not contain real API keys.

The UI placeholders such as `sk-ant-...`, `sk-...`, `AIza...`, and `hf_...` are examples only.

Recommended pre-approval checks:

```bash
git status --short
rg -n -i "sk-ant-|sk-[A-Za-z0-9]|hf_[A-Za-z0-9]|AIza|secret|password|token" .
```

Reviewers should distinguish example placeholders from real credentials.

## Dependency And Supply-Chain Review

Primary dependency manifests:

```text
cleanmol/backend/requirements.txt
cleanmol/frontend/package.json
cleanmol/frontend/package-lock.json
```

High-level dependency categories:

- FastAPI / Uvicorn for the local backend
- PyMuPDF for PDF extraction
- RDKit for chemistry validation
- Requests and provider SDKs for outbound API calls
- OpenPyXL for Excel output
- Next.js / React / Tailwind for the local frontend

CISO considerations:

- Review package licenses.
- Review known vulnerabilities before approval.
- Prefer enterprise package mirrors.
- Pin all Python transitive dependencies for controlled environments.
- Generate SBOMs if required by organizational policy.
- Re-run dependency scans before public or institutional releases.

## Privacy And Data Classification Guidance

Before use, classify the data being processed:

- public literature
- unpublished manuscripts
- patent-sensitive material
- proprietary assay data
- contract-restricted documents
- export-controlled data
- regulated personal data
- environmental, clinical, or toxicology data under special governance

CleanMol should not be used on restricted data until:

1. the workstation is approved
2. external providers are approved
3. provider retention/training settings are understood
4. data processing agreements are in place where required
5. egress controls are configured
6. output storage is approved

## Browser And Extension Risks

Because CleanMol uses a local browser UI:

- browser extensions can affect page behavior
- browser extensions may see page content depending on permissions
- browser profile compromise can expose localStorage
- shared browser profiles are not recommended

Recommended controls:

- use a dedicated managed browser profile
- disable unapproved extensions
- clear localStorage after reviews
- avoid running CleanMol in a personal browser profile for sensitive work

## How To Clear Stored API Keys

CleanMol does not yet include a one-click "clear secrets" button.

Current options:

1. Open browser developer tools and clear site data for the CleanMol localhost origin.
2. Clear local storage for `http://localhost:<port>` and `http://127.0.0.1:<port>` if used.
3. Use a dedicated browser profile and delete the profile after review.

Future enterprise hardening should add a visible "Clear API Keys" control and OS-level secure secret storage.

## FAIR Chemistry / UMA Security Notes

FAIR Chemistry / UMA is optional.

CleanMol prepares `fairchem_uma_candidates.csv` as a review handoff file. CleanMol does not automatically submit candidates to the FairChem leaderboard.

If a user separately installs FairChem or downloads UMA checkpoints:

- Hugging Face access may be required
- gated model terms may apply
- model files may be large
- GPU/cloud execution may introduce additional security review requirements
- outputs should be treated as derived research artifacts

## No Hidden Scientific Or Security Assurance

CleanMol does not certify:

- antimicrobial efficacy
- toxicity safety
- synthesis feasibility
- formulation safety
- regulatory readiness
- absence of software vulnerabilities
- absence of supply-chain risk
- provider compliance

CleanMol output is a research triage aid and must be reviewed by qualified experts.

## Known Security Limitations

Current known limitations:

- no built-in authentication
- no built-in authorization
- no TLS layer in the local app
- no encrypted local output store
- API keys stored in browser localStorage
- broad localhost CORS allowance
- dependency install requires external package registries by default
- no bundled SBOM
- no formal penetration test report
- no sandbox around user-selected input/output directories
- no malware scanning for PDFs or uploaded spreadsheets
- no enterprise audit trail
- no centralized policy engine for egress decisions

These limitations are acceptable for a local research preview on a controlled workstation, but they must be addressed before enterprise hosting or sensitive-data production use.

## Suggested CISO Approval Checklist

Use this checklist before approval:

1. Confirm intended deployment is single-user localhost.
2. Confirm workstation is managed, encrypted, and protected.
3. Confirm no prohibited data class will be processed.
4. Confirm approved external providers for Anthropic, OpenAI, Google, Hugging Face, ChEMBL, PubChem, NCI/CIR, OPSIN, and any optional FairChem workflows.
5. Confirm provider data retention and training settings.
6. Confirm outbound domains are allowlisted or blocked according to policy.
7. Confirm API keys are scoped, monitored, and rotatable.
8. Confirm output directory is approved storage.
9. Confirm browser profile and extension policy.
10. Confirm package installation comes from approved registries.
11. Run vulnerability and license scans.
12. Review CORS and localhost exposure.
13. Review whether Google Fonts fetches are allowed or should be vendored locally.
14. Decide whether public-source pulls are allowed.
15. Decide whether uploaded XLSM files are allowed.
16. Decide whether logs can be shared for troubleshooting.
17. Confirm users understand that outputs are not proof of efficacy, safety, synthesis readiness, or regulatory readiness.

## Suggested Network Allowlist

Only approve the domains needed for the selected workflow.

Install-time:

```text
pypi.org
files.pythonhosted.org
registry.npmjs.org
nodejs.org
brew.sh
github.com
```

Runtime LLM/model/data workflows:

```text
api.anthropic.com
api.openai.com
generativelanguage.googleapis.com
api.google.dev
huggingface.co
datasets-server.huggingface.co
www.ebi.ac.uk
pubchem.ncbi.nlm.nih.gov
cactus.nci.nih.gov
opsin.ch.cam.ac.uk
fair-chem.github.io
fonts.googleapis.com
fonts.gstatic.com
```

Some organizations may choose to block Google Fonts and vendor local fonts instead.

## Recommended Enterprise Hardening Before Wider Deployment

Recommended improvements before institutional production use:

- add login and SSO
- add RBAC
- add CSRF protection for non-local deployments
- restrict CORS to a single exact origin
- add TLS for hosted deployment
- move secrets out of browser localStorage
- add a "Clear API Keys" button
- add provider allow/deny policy switches
- add local-only/offline mode controls
- add an SBOM
- add dependency vulnerability scanning to CI
- add file size limits and file scanning
- add structured security/audit logging
- add output encryption or integration with approved storage
- vendor fonts locally
- document a formal threat model
- complete a penetration test if deployed beyond localhost

## Vulnerability Reporting

Do not publish secrets, private datasets, unpublished research, or exploit details in public issues.

Use GitHub private vulnerability reporting if enabled for the repository. If private reporting is not available, contact the repository owner through a private channel and share only the minimum necessary technical detail until a secure reporting path is established.

## CISO Bottom Line

CleanMol Discovery is reasonable to evaluate as a local research preview on a controlled workstation with approved data and approved egress.

It should not be approved as a shared enterprise service or for sensitive restricted data without additional hardening, provider review, secrets management, audit controls, and data-governance approval.
