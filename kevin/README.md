# Kevin — Multi-Model Chemistry Dataset Builder

Kevin is a Windows-first (macOS compatible) desktop application that extracts structured chemistry datasets from born-digital PDFs using a multi-model AI pipeline.

## What It Does

Kevin takes a folder of PDFs (papers, patents) and produces:
- **SQLite database** (`dataset.db`) with molecules, experiments, results, evidence, audits, and repairs
- **JSONL exports** for each document
- **Bundle folders** containing extracted markdown, raw outputs, and provenance

### The Pipeline

1. **PDF → Bundle**: Extract page-anchored markdown from PDFs
2. **Opus 4.5 Extraction**: Claude extracts molecules, experiments, results with citations
3. **GPT-5.2 Audit**: Verifies every claim against the source text
4. **Auto-Repair**: Re-extracts items that failed audit
5. **Gemini Gap Hunt**: Finds missed data (tables, figures, molecules)
6. **Targeted Extraction**: Fills gaps with focused prompts
7. **Re-audit Loop**: Iterates until clean

## Quick Start (Windows)

### First-Time Installation

1. Make sure you have installed:
   - [Python 3.10+](https://www.python.org/downloads/) (check "Add to PATH" during install)
   - [Node.js 18+](https://nodejs.org/) (LTS version)

2. Double-click **`install.bat`** in the repository root, or run from command prompt:
   ```
   install.bat
   ```

3. Wait for installation to complete (typically 2-3 minutes)

### Running the Application

1. Double-click **`run.bat`** in the repository root, or run from command prompt:
   ```
   run.bat
   ```

2. Your browser will automatically open to http://localhost:3000

3. Enter your API keys and folder paths, then click "Run Pipeline"

### Stopping the Application

- Close the two terminal windows that opened, OR
- Double-click **`stop.bat`** to kill all servers

### Default Folders

The installer creates these folders for convenience:
- **Input:** `C:\Users\YourName\Kevin\input` (place PDFs here)
- **Output:** `C:\Users\YourName\Kevin\output` (dataset saved here)

---

## Manual Setup (Alternative)

If you prefer manual setup or are on macOS/Linux:

### Backend Setup
```powershell
cd kevin/backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8787
```

### Frontend Setup
```powershell
cd kevin/frontend
npm install
npm run dev
```

### Open the App

Navigate to: http://localhost:3000

### Configure

1. **API Keys**: Enter your Anthropic (required), OpenAI, and Gemini keys
2. **Folders**: Paste full paths (e.g., `C:\data\pdfs` and `C:\data\output`)
3. **Models**: Adjust model names if needed

### Run

Click "Run Pipeline" and watch the console output.

## Output Structure
```
output_folder/
├── dataset.db          # SQLite database
├── bundles/
│   └── doc_xxxxxxxx/
│       ├── paper.md
│       ├── metadata.json
│       ├── provenance.json
│       ├── extraction_opus.json
│       ├── audit_gpt52.json
│       ├── repair_report.json
│       ├── gaps_gemini.json
│       ├── extraction_repaired.json
│       └── ...
├── exports/
│   ├── doc_xxx_molecules.jsonl
│   ├── doc_xxx_experiments.jsonl
│   ├── doc_xxx_results.jsonl
│   └── doc_xxx_dataset.jsonl
└── logs/
```

## Database Schema

### Tables

- **documents**: PDF metadata and paths
- **molecules**: Extracted chemical entities
- **experiments**: Assay/protocol information
- **results**: Numeric outcomes with evidence
- **evidence**: Page/snippet citations
- **audits**: GPT-5.2 verification results
- **gap_suggestions**: Gemini-identified gaps
- **repairs**: Auto-repair history
- **runs**: Pipeline execution logs

## API Keys

The app uses three AI providers:

| Provider | Model | Role |
|----------|-------|------|
| Anthropic | claude-opus-4-5-20251101 | Primary chemist extractor |
| OpenAI | gpt-5.2-thinking | Citation auditor |
| Google | gemini-3-pro | Gap hunter |

Keys are stored in browser localStorage (never sent to any server except the respective API endpoints).

## Requirements

### Backend
- Python 3.10+
- FastAPI, PyMuPDF, requests

### Frontend
- Node.js 18+
- Next.js 14, React 18, Tailwind CSS

## macOS Setup

Same as Windows, but use:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

## License

MIT
