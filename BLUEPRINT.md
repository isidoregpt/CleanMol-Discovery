# Kevin Pipeline - Architecture Blueprint

> **Purpose**: This document provides a complete technical blueprint of the Kevin application for LLM understanding and development. Kevin is a multi-model AI pipeline that extracts structured chemistry datasets from scientific PDFs.

---

## 1. High-Level Overview

Kevin transforms scientific PDFs (papers and patents) into structured, audited chemistry datasets. It uses a multi-model approach where different AI models handle different stages of the pipeline.

### Core Value Proposition
- **Input**: Born-digital PDFs containing chemistry research (QAC/biocide studies, MIC data, virulence assays)
- **Output**: Structured JSONL/Excel datasets with molecules, experiments, results, and full provenance
- **Key Differentiator**: Multi-model extraction → audit → repair → gap-hunting loop that compounds quality

### Target Domain
Quaternary ammonium compounds (QACs), cationic biocides, antimicrobial resistance, MIC data, biofilm assays, virulence phenotypes.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              KEVIN PIPELINE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │   FRONTEND   │    │   BACKEND    │    │   STORAGE    │                  │
│  │  (Next.js)   │───▶│  (FastAPI)   │───▶│  (SQLite)    │                  │
│  │  Port 3000   │    │  Port 8787   │    │  dataset.db  │                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
│                              │                                               │
│                              ▼                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                        MODEL ROUTING LAYER                            │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │  Primary Extractor  │  Auditor         │  Gap Hunter    │  Worker     │ │
│  │  Claude Opus 4.5    │  GPT-5.2 Thinking│  Gemini 3 Pro  │  Sonnet 4.5 │ │
│  │  (chemistry)        │  (verification)  │  (coverage)    │  (ops)      │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Directory Structure

```
kevin/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── pipeline.py             # Main orchestration
│   │   ├── db.py                   # SQLite database layer
│   │   ├── pdf_bundle.py           # PDF → bundle extraction
│   │   ├── figure_analysis.py      # GPT-4o figure/structure extraction
│   │   ├── context_slice.py        # Page slicing utilities
│   │   ├── json_utils.py           # JSON parsing helpers
│   │   ├── export_jsonl.py         # JSONL/Excel export
│   │   │
│   │   ├── llm_anthropic.py        # Anthropic API client
│   │   ├── llm_openai.py           # OpenAI API client
│   │   ├── llm_gemini.py           # Gemini API client
│   │   │
│   │   ├── prompts_opus.py         # Opus extraction prompts
│   │   ├── prompts_audit.py        # GPT-5.2 audit prompts
│   │   ├── prompts_gap.py          # Gemini gap-hunt prompts
│   │   ├── prompts_repair.py       # Repair prompts
│   │   ├── prompts_targeted.py     # Targeted extraction prompts
│   │   │
│   │   ├── extract_opus.py         # Opus extraction logic
│   │   ├── audit_and_gap.py        # Audit + gap detection
│   │   ├── repair_opus.py          # Entity repair logic
│   │   ├── auto_repair.py          # Automated repair orchestration
│   │   ├── gap_resolve.py          # Gap resolution with targeted extraction
│   │   ├── smiles_lookup.py        # PubChem SMILES lookup
│   │   └── smiles_validation.py    # RDKit SMILES validation
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                # Home screen with API keys + folders
│   │   ├── globals.css
│   │   └── components/
│   │       ├── Card.tsx
│   │       ├── Field.tsx
│   │       ├── Button.tsx
│   │       └── LogConsole.tsx
│   │
│   ├── package.json
│   ├── tailwind.config.js
│   └── next.config.js
│
└── output/                         # Generated per-run
    ├── dataset.db                  # SQLite database
    ├── bundles/
    │   └── doc_XXXX/
    │       ├── paper.md            # Extracted text with [[PAGE N]] anchors
    │       ├── metadata.json
    │       ├── provenance.json
    │       ├── extraction_opus.json
    │       ├── audit_gpt52.json
    │       ├── gaps_gemini.json
    │       ├── extraction_repaired.json
    │       └── figure_analysis.json
    ├── exports/
    │   ├── doc_XXXX_molecules.jsonl
    │   ├── doc_XXXX_experiments.jsonl
    │   ├── doc_XXXX_results.jsonl
    │   └── doc_XXXX_review.xlsx
    └── logs/

```

---

## 4. Database Schema

SQLite database (`dataset.db`) with the following tables:

### Core Tables

```sql
-- Document registry
CREATE TABLE documents (
    doc_id TEXT PRIMARY KEY,        -- e.g., "doc_927240911470"
    source_type TEXT NOT NULL,      -- "paper" | "patent"
    title TEXT,
    doi TEXT,
    year INTEGER,
    path TEXT NOT NULL,             -- Original PDF path
    bundle_path TEXT NOT NULL,      -- Bundle folder path
    created_at TEXT NOT NULL
);

-- Extracted molecules
CREATE TABLE molecules (
    molecule_id TEXT PRIMARY KEY,   -- e.g., "BAC", "PHL-6-8"
    name_as_written TEXT,           -- Exact name from paper
    normalized_name TEXT,           -- Cleaned/standardized name
    smiles TEXT,                    -- Chemical structure (SMILES notation)
    inchi_key TEXT,                 -- Unique chemical identifier
    total_nitrogen_count INTEGER,
    quaternary_n_count INTEGER,
    formal_charge INTEGER,
    head_group_class TEXT,          -- "quaternary ammonium", "biguanide", etc.
    chain_lengths TEXT,             -- JSON array, e.g., "[10,10]"
    created_at TEXT NOT NULL
);

-- Experimental conditions
CREATE TABLE experiments (
    experiment_id TEXT PRIMARY KEY, -- e.g., "EXP1"
    doc_id TEXT NOT NULL,
    organism TEXT,                  -- e.g., "Pseudomonas aeruginosa"
    strain TEXT,                    -- e.g., "PAO1", "ATCC 27853"
    assay_type TEXT,                -- e.g., "MIC", "biofilm", "hemolysis"
    conditions TEXT,                -- JSON object
    exposure_protocol TEXT,         -- JSON object
    created_at TEXT NOT NULL,
    FOREIGN KEY(doc_id) REFERENCES documents(doc_id)
);

-- Experimental results
CREATE TABLE results (
    result_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    experiment_id TEXT NOT NULL,
    molecule_id TEXT,
    endpoint TEXT,                  -- e.g., "MIC", "fold_change", "lysis20"
    value REAL,
    units TEXT,                     -- e.g., "μM", "μg/mL"
    directionality TEXT,            -- "up" | "down" | null
    confidence REAL,                -- 0.0 to 1.0
    evidence_json TEXT NOT NULL,    -- Citation details
    created_at TEXT NOT NULL,
    FOREIGN KEY(doc_id) REFERENCES documents(doc_id),
    FOREIGN KEY(experiment_id) REFERENCES experiments(experiment_id),
    FOREIGN KEY(molecule_id) REFERENCES molecules(molecule_id)
);

-- Evidence citations for provenance
CREATE TABLE evidence (
    evidence_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    kind TEXT NOT NULL,             -- "snippet" | "table_cell" | "figure_caption"
    page INTEGER,
    table_id TEXT,
    cell TEXT,
    snippet TEXT,
    source_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(doc_id) REFERENCES documents(doc_id)
);
```

### Audit/QA Tables

```sql
-- GPT-5.2 audit results
CREATE TABLE audits (
    audit_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,      -- "molecule" | "experiment" | "result"
    entity_id TEXT NOT NULL,
    model TEXT NOT NULL,
    verdict TEXT NOT NULL,          -- "SUPPORTED" | "AMBIGUOUS" | "REJECT"
    confidence REAL NOT NULL,
    issues_json TEXT,               -- JSON array of issue descriptions
    suggested_fix_json TEXT,        -- JSON object with corrections
    created_at TEXT NOT NULL
);

-- Gemini gap suggestions
CREATE TABLE gap_suggestions (
    suggestion_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    model TEXT NOT NULL,
    kind TEXT NOT NULL,             -- "missing_molecule" | "table_to_parse" | etc.
    page INTEGER,
    description TEXT NOT NULL,
    rationale TEXT,
    created_at TEXT NOT NULL
);

-- Auto-repair history
CREATE TABLE repairs (
    repair_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    model TEXT NOT NULL,
    reason TEXT NOT NULL,           -- e.g., "audit:AMBIGUOUS"
    before_json TEXT NOT NULL,
    after_json TEXT NOT NULL,
    applied INTEGER NOT NULL,       -- 1 = applied, 0 = failed
    created_at TEXT NOT NULL
);

-- Pipeline run history
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    input_dir TEXT NOT NULL,
    output_dir TEXT NOT NULL,
    primary_model TEXT NOT NULL,
    auditor_model TEXT NOT NULL,
    gap_model TEXT NOT NULL,
    status TEXT NOT NULL,           -- "ok" | "failed"
    notes TEXT
);
```

---

## 5. Pipeline Stages (Detailed)

### Stage 1: PDF Extraction
**Module**: `pdf_bundle.py`
**Input**: PDF file
**Output**: Bundle folder with `paper.md`

```python
def extract_bundle(pdf_path: Path, bundle_root: Path) -> dict:
    # 1. Generate stable doc_id from file hash
    doc_id = stable_doc_id(pdf_path)  # e.g., "doc_927240911470"
    
    # 2. Extract text with page anchors
    pdf = fitz.open(pdf_path)
    for page_idx, page in enumerate(pdf, start=1):
        text = page.get_text("text")
        md_lines.append(f"\n\n[[PAGE {page_idx}]]\n")
        md_lines.append(text)
    
    # 3. Save bundle files
    (bundle_dir / "paper.md").write_text(paper_md)
    (bundle_dir / "metadata.json").write_text(...)
    (bundle_dir / "provenance.json").write_text(...)
```

### Stage 2: Figure Analysis
**Module**: `figure_analysis.py`
**Model**: GPT-4o (vision)
**Purpose**: Extract chemical structures from figures

```python
def analyze_figures(pdf_path: Path, bundle_dir: Path) -> dict:
    # 1. Extract images from PDF
    images = extract_pdf_images(pdf_path)
    
    # 2. Send each image to GPT-4o with structured prompt
    for img in images:
        response = call_gpt4o_vision(
            image=img,
            prompt="Extract all chemical structures. For each, provide: name, SMILES..."
        )
        structures.extend(parse_structures(response))
    
    # 3. Validate SMILES (optional - RDKit)
    for structure in structures:
        if structure.smiles:
            structure.valid = validate_smiles(structure.smiles)
```

### Stage 3: Opus Extraction
**Module**: `extract_opus.py`
**Model**: Claude Opus 4.5
**Purpose**: Extract molecules, experiments, results with citations

**System Prompt**:
```
You are Kevin, an expert chemist and scientific literature reviewer.
Rules:
- Do NOT guess. If unsupported, use null/omit.
- Every extracted molecule/experiment/result MUST include evidence with a PAGE anchor.
- Output valid JSON only.
```

**Expected Output Schema**:
```json
{
  "doc": {"title": "...", "doi": "...", "year": 2024, "organisms": ["P. aeruginosa"]},
  "molecules": [
    {
      "molecule_id": "BAC",
      "name_as_written": "benzalkonium chloride",
      "smiles": "CCCCCCCCCCCC[N+](C)(C)Cc1ccccc1.[Cl-]",
      "head_group_class": "quaternary ammonium",
      "evidence": {"kind": "snippet", "page": 2, "snippet": "benzalkonium chloride (BAC)..."}
    }
  ],
  "experiments": [...],
  "results": [...]
}
```

### Stage 4: GPT-5.2 Audit
**Module**: `audit_and_gap.py`
**Model**: GPT-5.2 Thinking
**Purpose**: Verify every extracted field against source text

**Verdicts**:
- `SUPPORTED`: Clearly supported by cited evidence
- `AMBIGUOUS`: Partial support, needs review
- `REJECT`: Not supported by evidence

```json
{
  "audits": [
    {
      "entity_type": "molecule",
      "entity_id": "BAC",
      "verdict": "SUPPORTED",
      "confidence": 0.95,
      "issues": [],
      "suggested_fix": null
    },
    {
      "entity_type": "result",
      "entity_id": "RES5",
      "verdict": "AMBIGUOUS",
      "confidence": 0.6,
      "issues": ["Value not explicitly stated on cited page"],
      "suggested_fix": {"value": null, "notes": "Value inferred from figure, not text"}
    }
  ]
}
```

### Stage 5: Auto-Repair
**Module**: `auto_repair.py`
**Model**: Claude Opus 4.5 (targeted)
**Purpose**: Fix AMBIGUOUS/REJECT items with page-specific context

```python
def auto_repair(extraction, audit_json, paper_md):
    for audit in audit_json["audits"]:
        if audit["verdict"] in ["AMBIGUOUS", "REJECT"]:
            # 1. Get page context around the citation
            page_slice = slice_pages(paper_md, [audit["evidence"]["page"]], pad=1)
            
            # 2. Ask Opus to repair with limited context
            repair_result = repair_entity_with_opus(
                entity=extraction[audit["entity_type"]][audit["entity_id"]],
                page_slice=page_slice,
                issues=audit["issues"]
            )
            
            # 3. Update database
            if repair_result["repaired_entity"]:
                update_entity(conn, repair_result["repaired_entity"])
```

### Stage 6: Gemini Gap Hunt
**Module**: `audit_and_gap.py`
**Model**: Gemini 3 Pro
**Purpose**: Find missed extractions

```json
{
  "gaps": [
    {
      "kind": "table_to_parse",
      "page": 5,
      "description": "Table 2 contains MIC values not yet extracted",
      "rationale": "Table shows MIC for 12 compounds against 4 bacterial strains"
    },
    {
      "kind": "missing_molecule",
      "page": 3,
      "description": "Compound PHL-10-10 mentioned but not in molecules list"
    }
  ]
}
```

### Stage 7: Gap Resolution
**Module**: `gap_resolve.py`
**Model**: Claude Opus 4.5 (targeted)
**Purpose**: Extract additional entities from identified gaps

```python
def resolve_gaps_with_targeted_opus(extraction, gaps_json, paper_md):
    for gap in gaps_json["gaps"]:
        if gap["page"]:
            page_slice = slice_pages(paper_md, [gap["page"]], pad=1)
            additions = targeted_extraction(page_slice, gap)
            extraction = merge_additions(extraction, additions)
    return extraction
```

### Stage 8: SMILES Enrichment
**Module**: `smiles_lookup.py`
**Sources**: PubChem API, Figure Analysis results

```python
def enrich_smiles(molecules):
    for mol in molecules:
        if not mol.smiles:
            # 1. Try figure analysis results
            fig_smiles = figure_smiles_map.get(mol.name_as_written)
            if fig_smiles:
                mol.smiles = fig_smiles
                mol.smiles_source = "figure_extraction"
                continue
            
            # 2. Try PubChem lookup
            pubchem_smiles = lookup_pubchem(mol.name_as_written)
            if pubchem_smiles:
                mol.smiles = pubchem_smiles
                mol.smiles_source = "PubChem"
```

### Stage 9: Export
**Module**: `export_jsonl.py`
**Outputs**: JSONL files, Excel workbook, merge files

---

## 6. Model Routing Configuration

```python
DEFAULT_MODELS = {
    "primary": "claude-opus-4-5-20251101",      # Chemistry extraction
    "auditor": "gpt-5.2-2025-12-11",            # Citation verification
    "gapHunter": "gemini-3-pro-preview",        # Coverage analysis
    "figureAnalysis": "gpt-4o-2024-11-20",      # Structure extraction from images
    "worker": "claude-sonnet-4-5-20250929"      # Batch operations
}
```

### Why Multi-Model?

| Model | Strength | Use Case |
|-------|----------|----------|
| Opus 4.5 | Deep reasoning, chemistry understanding | Primary extraction, repairs |
| GPT-5.2 | Citation faithfulness, factual verification | Audit pass |
| Gemini 3 Pro | Long context (1M tokens), gap detection | Finding missed content |
| GPT-4o | Vision capabilities | Figure/structure extraction |

---

## 7. API Endpoints

### Backend (FastAPI)

```python
# Main pipeline endpoint
POST /api/run
{
    "input_dir": "C:\\PDFs",
    "output_dir": "C:\\Output",
    "models": {
        "primary": "claude-opus-4-5-20251101",
        "auditor": "gpt-5.2-2025-12-11",
        "gapHunter": "gemini-3-pro-preview"
    },
    "keys": {
        "anthropic": "sk-ant-...",
        "openai": "sk-...",
        "gemini": "AIza..."
    },
    "options": {
        "max_gap_rounds": 2
    }
}

# Response
{
    "ok": true,
    "run": {
        "run_id": "3748c8b7-698b-41b6-a6d3-e03bdf23f17f",
        "status": "ok",
        "documents_processed": ["doc_927240911470", "doc_f17935ab1e97"],
        "errors": []
    }
}
```

---

## 8. Data Flow Diagram

```
┌─────────┐     ┌──────────────┐     ┌────────────────┐
│  PDF    │────▶│ PDF Bundle   │────▶│ paper.md       │
│  File   │     │ Extraction   │     │ + page anchors │
└─────────┘     └──────────────┘     └───────┬────────┘
                                              │
     ┌────────────────────────────────────────┼────────────────────────────────────┐
     │                                        ▼                                     │
     │  ┌───────────────┐    ┌───────────────────────────┐    ┌────────────────┐  │
     │  │ Figure        │    │ Opus Primary Extraction   │    │ GPT-5.2 Audit  │  │
     │  │ Analysis      │    │ (molecules, experiments,  │───▶│ (verify each   │  │
     │  │ (GPT-4o)      │    │  results with citations)  │    │  citation)     │  │
     │  └───────┬───────┘    └───────────────────────────┘    └───────┬────────┘  │
     │          │                                                      │           │
     │          │            ┌───────────────────────────┐            │           │
     │          │            │   Auto-Repair Loop        │◀───────────┘           │
     │          │            │   (fix AMBIGUOUS items)   │                        │
     │          │            └───────────────────────────┘                        │
     │          │                         │                                        │
     │          │            ┌────────────▼────────────┐                          │
     │          │            │  Gemini Gap Hunt        │                          │
     │          │            │  (find missed content)  │                          │
     │          │            └────────────┬────────────┘                          │
     │          │                         │                                        │
     │          │            ┌────────────▼────────────┐                          │
     │          │            │  Gap Resolution Loop    │                          │
     │          │            │  (targeted extraction)  │                          │
     │          │            └────────────┬────────────┘                          │
     │          │                         │                                        │
     │          ▼                         ▼                                        │
     │  ┌───────────────────────────────────────────────────────────────────────┐│
     │  │                    SMILES Enrichment                                   ││
     │  │  1. Figure-derived SMILES  2. PubChem lookup  3. Known structures     ││
     │  └───────────────────────────────────────────────────────────────────────┘│
     │                                    │                                        │
     └────────────────────────────────────┼────────────────────────────────────────┘
                                          ▼
                    ┌─────────────────────────────────────────┐
                    │              OUTPUTS                    │
                    │  • SQLite database (dataset.db)         │
                    │  • JSONL files (molecules, experiments) │
                    │  • Excel workbook (review.xlsx)         │
                    │  • Merge files (unified_dataset.xlsx)   │
                    └─────────────────────────────────────────┘
```

---

## 9. Key Design Decisions

### 9.1 Provenance-First Extraction
Every extracted fact MUST include:
- Page number
- Exact snippet or table cell reference
- Entity this applies to

**Why**: Makes dataset defensible, auditable, and debuggable.

### 9.2 Page Anchors (`[[PAGE N]]`)
All paper text includes page markers:
```markdown
[[PAGE 3]]
Benzalkonium chloride (BAC) showed MIC values...

[[PAGE 4]]
Table 1 presents the antibacterial activity...
```

**Why**: Enables targeted extraction and repair without re-reading entire documents.

### 9.3 Multi-Round Gap Resolution
Pipeline runs gap detection + resolution multiple times (default: 2 rounds):
```
Round 1: Find gaps → Extract → Re-audit
Round 2: Find remaining gaps → Extract → Final audit
```

**Why**: Single-pass extraction misses ~20-30% of extractable content.

### 9.4 Separate Models for Separate Tasks
- **Extraction** (Opus): Needs deep reasoning, chemistry understanding
- **Audit** (GPT-5.2): Needs strict factual verification
- **Gap Hunt** (Gemini): Needs broad pattern recognition, long context

**Why**: Each model excels at different aspects; combining them produces better results than any single model.

---

## 10. Error Handling

### Known Issues and Mitigations

| Issue | Mitigation |
|-------|------------|
| Gemini returns invalid JSON | Parse with fallback, continue with empty gaps |
| SMILES validation fails (RDKit DLL) | Skip validation, mark as unvalidated |
| Opus returns partial extraction | Re-prompt with targeted page context |
| PubChem lookup fails | Use figure-derived SMILES or mark as missing |

### Error Categories

```python
class PipelineError:
    FATAL = "fatal"      # Stop processing this document
    WARNING = "warning"  # Log and continue
    RECOVERABLE = "recoverable"  # Retry with fallback
```

---

## 11. Output Files Specification

### 11.1 JSONL Files

**molecules.jsonl** (one molecule per line):
```json
{"molecule_id": "BAC", "name_as_written": "benzalkonium chloride", "smiles": "CCCCCCCCCCCC[N+](C)(C)Cc1ccccc1.[Cl-]", "head_group_class": "quaternary ammonium", "smiles_source": "PubChem"}
{"molecule_id": "PHL-6-8", "name_as_written": "PHL-6,8", "smiles": "...", "head_group_class": "quaternary ammonium", "smiles_source": "figure_extraction"}
```

**experiments.jsonl**:
```json
{"experiment_id": "EXP1", "doc_id": "doc_927240911470", "organism": "Staphylococcus aureus", "assay_type": "MIC", "conditions": {"media": "MHB", "time": "24h"}}
```

**results.jsonl**:
```json
{"result_id": "RES1", "experiment_id": "EXP1", "molecule_id": "PHL-6-8", "endpoint": "MIC", "value": 2.0, "units": "μM", "confidence": 0.9}
```

### 11.2 Excel Workbook

**unified_dataset.xlsx** sheets:
- Summary: Run stats, coverage metrics
- Molecules: All extracted molecules with SMILES
- Experiments: All experiments with conditions
- Results: All results with citations
- Missing SMILES: Molecules needing manual SMILES entry

### 11.3 Machine Learning Ready

**analysis_ready.csv**: Flattened format for ML:
```csv
molecule_id,name,smiles,organism,assay_type,endpoint,value,units,doc_id
BAC,benzalkonium chloride,CCCCCCCCCCCC[N+]...,S. aureus,MIC,MIC,4.0,μM,doc_927240911470
```

---

## 12. Configuration Reference

### Environment Variables (Optional)
```bash
KEVIN_ANTHROPIC_KEY=sk-ant-...
KEVIN_OPENAI_KEY=sk-...
KEVIN_GEMINI_KEY=AIza...
```

### Runtime Options
```json
{
    "max_gap_rounds": 2,           // Number of gap resolution iterations
    "skip_audit": false,           // Skip GPT-5.2 audit (faster, less accurate)
    "skip_figures": false,         // Skip figure analysis
    "smiles_validation": true,     // Run RDKit validation
    "export_formats": ["jsonl", "xlsx", "csv"]
}
```

---

## 13. Performance Characteristics

### Typical Run (3 PDFs, ~20 pages total)
- **Duration**: 30-60 minutes
- **API Calls**: ~30-50 Anthropic, ~10-20 OpenAI, ~5-10 Gemini
- **Tokens**: ~200K input, ~50K output (Anthropic)
- **Cost**: ~$5-15 USD

### Bottlenecks
1. **Audit stage**: GPT-5.2 reasoning takes 2-5 min per document
2. **Figure analysis**: GPT-4o vision calls are slow (~10s each)
3. **Gap resolution**: Multiple Opus calls per round

---

## 14. Extension Points

### Adding New Extraction Targets
1. Update `prompts_opus.py` with new schema fields
2. Add database columns in `db.py`
3. Update export in `export_jsonl.py`

### Adding New Models
1. Create `llm_newprovider.py` with API client
2. Add to model routing in `pipeline.py`
3. Update frontend model selector

### Adding New Output Formats
1. Create exporter in `export_*.py`
2. Register in pipeline export stage
3. Add to `export_formats` option

---

## 15. Known Limitations

1. **SMILES Accuracy**: Figure extraction has ~70-90% accuracy; chain length errors common
2. **Table Parsing**: Complex tables with merged cells may be missed
3. **Patent Support**: Optimized for papers; patents need prompt tuning
4. **RDKit on Windows**: DLL loading issues; validation may be skipped
5. **Rate Limits**: Heavy API usage; may need retry logic for large batches

---

## 16. Troubleshooting

### "No JSON object found in model output"
- **Cause**: Model returned prose instead of JSON
- **Fix**: Retry with stricter prompt, or use fallback empty result

### "SMILES validation failed"
- **Cause**: Invalid SMILES string or RDKit DLL issue
- **Fix**: Check figure extraction, try PubChem lookup

### "Audit found no items"
- **Cause**: Extraction returned empty or malformed JSON
- **Fix**: Check `extraction_opus.json` in bundle folder

### Pipeline hangs at audit stage
- **Cause**: OpenAI API timeout
- **Fix**: Increase timeout, check API status

---

*Document Version: 1.0*
*Last Updated: January 2026*
*For the latest code, see the kevin/ repository*
