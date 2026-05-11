# TALASH (Talent Acquisition & Learning Automation for Smart Hiring)
CS-417: Large Language Models

TALASH is a full-stack LLM-powered recruitment system for CV processing, candidate assessment, and hiring insights.

## Setup & Run

### Environment

Copy `.env.example` to `.env` and set your keys. Example:

```
GEMINI_API_KEY=
CSV_OUTPUT_DIR=./output
ASSESSMENTS_DIR=./data/candidates_assessments
INPUT_CVS_DIR=./data/input_cvs
GEMINI_MODEL=gemini-3.1-flash-lite-preview
HOST=0.0.0.0
PORT=8000
DEBUG=true
FRONTEND_URL=http://localhost:5173
JWT_SECRET=talash-m3-secret-key-2025
JWT_EXPIRE_MINUTES=480
DATABASE_URL=sqlite:///./talash.db
GROQ_API_KEY=
```

### Install & Run

```powershell
# Backend dependencies
pip install -r requirements.txt

# Frontend dependencies
cd frontend
npm install
cd ..

# Start API server (port 8000)
uvicorn backend.main:app --reload --port 8000

# Start frontend (port 5173)
cd frontend
npm run dev
```

### Optional: Run Analysis Pipeline

```powershell
# Generate candidate assessments from M1 CSV outputs
python -m analysis.batch_processor --input-csvs ./output --output ./data/candidates_assessments
```

## Project Structure

```
.
├── analysis/
│   ├── __init__.py
│   ├── batch_processor.py
│   ├── data_loader.py
│   ├── educational_analysis.py
│   ├── employment_analysis.py
│   ├── groq_fallback.py
│   ├── missing_info_analysis.py
│   ├── ranking.py
│   ├── regex_rank_lookup.py
│   ├── research_analysis.py
│   └── summary_generation.py
├── backend/
│   ├── __init__.py
│   ├── auth.py
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── schemas.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── analytics.py
│   │   ├── auth.py
│   │   ├── candidates.py
│   │   └── jobs.py
│   └── services/
│       ├── __init__.py
│       ├── assessment_service.py
│       ├── candidate_service_legacy.py
│       └── candidate_service.py
├── data/
│   ├── candidates_assessments/
│   ├── input_cvs/
│   ├── journal_ranks.json
│   ├── qs_ranks.json
│   └── research_verification_cache.json
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── index.css
│       ├── main.jsx
│       ├── pages/
│       │   ├── AnalyticsPage.jsx
│       │   ├── CandidateDetailPage.jsx
│       │   ├── CandidateListPage.jsx
│       │   ├── DashboardPage.jsx
│       │   ├── JobsPage.jsx
│       │   ├── LoginPage.jsx
│       │   └── ProcessingPage.jsx
│       └── services/
│           └── api.js
├── output/
├── tests/
│   ├── __init__.py
│   ├── test_m2_analysis.py
│   └── test_m2_integration.py
├── cli.py
├── extraction.py
├── io_csv.py
├── manage.py
├── models.py
├── normalization.py
├── preprocessing_script.py
├── README.md
├── requirements.txt
├── run_all.bat
└── run_preprocessing.ps1
```

Below is the milestone by milestone progression of this project.

## Milestone 1 — Preprocessing Runner

### Code Layout

- [models.py](models.py): Pydantic schemas, extraction result dataclass, and table column contracts.
- [normalization.py](normalization.py): Parsing, normalization, and relational row flattening logic.
- [io_csv.py](io_csv.py): CSV append/overwrite persistence helpers.
- [extraction.py](extraction.py): PDF reading, Gemini extraction call, and batch processing orchestration.
- [cli.py](cli.py): Argument parsing and app entry logic.
- [preprocessing_script.py](preprocessing_script.py): Compatibility wrapper so existing commands still work.

### Quick run (single PDF)

```powershell
.\run_preprocessing.ps1 ".\Handler (8)-21-29.pdf"
```

### Quick run (folder ingestion)

```powershell
.\run_preprocessing.ps1 ".\CVs"
```

### Wrapper overwrite mode

```powershell
.\run_preprocessing.ps1 ".\CVs" -Overwrite
```

### Python CLI options

```powershell
# Single PDF (short positional input)
.\.venv\Scripts\python.exe .\preprocessing_script.py ".\Handler (8)-21-29.pdf"

# Folder ingestion (processes all PDFs one by one)
.\.venv\Scripts\python.exe .\preprocessing_script.py ".\CVs"

# Overwrite mode (default behavior is append)
.\.venv\Scripts\python.exe .\preprocessing_script.py ".\CVs" --overwrite
```

Notes:
- By default, output CSV files are appended to, not overwritten.
- Use `--overwrite` on the Python CLI or `-Overwrite` on the PowerShell wrapper when you want fresh CSVs for a new run.

---

## Milestone 2 — Analysis & Web Application

### Setup

```powershell
# 1. Install M2 Python dependencies
pip install -r requirements.txt

# 2. Install frontend dependencies
cd frontend
npm install
cd ..

# 3. Copy .env.example to .env and set your GEMINI_API_KEY
copy .env.example .env

# 4. Add GROQ_API_KEY for Groq fallback ranking/topic inference
# GROQ model default: llama-3.1-8b-instant
```

### Run M2 Analysis Pipeline

```powershell
# Generate candidate assessments from M1 CSV outputs
python -m analysis.batch_processor --input-csvs ./output --output ./data/candidates_assessments
```

### Research Profile Analysis (Enhanced)

The research module now produces evidence-backed journal and conference evaluation with:

- journal legitimacy and indexing reasoning (WoS/Scopus verification signals, quartile/IF enrichment, predatory-risk indicators),
- conference quality interpretation (CORE rank mapping, series maturity, proceedings reputation),
- contribution-aware authorship analysis (first/corresponding/last/middle/sole with contribution significance),
- recruiter-facing summaries (`research_assessment.recruiter_summary`) with key indicators and risk flags,
- confidence and evidence-gap tracking per publication for incomplete CV robustness,
- deep topic variability analysis (semantic clustering, domain percentages, evolution timeline, concentration/dispersion and explainable variability score),
- collaboration intelligence (network density proxy, recurring/one-time collaborators, stable groups, leadership and supervision-style signals),
- enriched books/patents analytics (authorship-role inference, publisher/ISBN quality, verification states, innovation orientation, translation capability).
- fallback ranking pipeline: Gemini/verified extraction -> Groq JSON-context lookup -> deterministic high-rank fallback (800-1000).

Custom ranking context files:
- `data\UniversityRankings.json`
- `data\JournalRankings.json`

### Run FastAPI Backend

```powershell
# Start the API server (port 8000)
cd CS-417-Project
uvicorn backend.main:app --reload --port 8000

# API docs: http://localhost:8000/docs
```

### Run React Frontend

```powershell
# Start the dev server (port 5173)
cd frontend
npm run dev

# Open: http://localhost:5173
```

### Run Tests

```powershell
# Run all M2 tests
python -m pytest tests/ -v
```

### M2 File Structure

```
├── analysis/                    (M2 - Analysis Modules)
│   ├── educational_analysis.py  # Educational profile assessment
│   ├── employment_analysis.py   # Employment profile analysis
│   ├── missing_info_analysis.py # Missing info detection & emails
│   ├── summary_generation.py    # Overall scoring & summaries
│   ├── data_loader.py           # CSV data loading utilities
│   └── batch_processor.py       # Batch processing CLI
├── backend/                     (M2 - FastAPI Backend)
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Configuration settings
│   ├── schemas.py               # Pydantic response models
│   ├── routes/candidates.py     # 7 REST API endpoints
│   └── services/                # Business logic
├── frontend/                    (M2 - React Frontend)
│   └── src/
│       ├── App.jsx              # Main app with routing
│       ├── pages/               # Dashboard, Candidates, Detail, Processing
│       └── services/api.js      # Axios API client
├── tests/                       (M2 - Tests)
│   ├── test_m2_analysis.py      # Unit tests
│   └── test_m2_integration.py   # Integration tests
├── data/candidates_assessments/ # M2 JSON assessment outputs
└── M2_CHANGES.md                # M2 changes documentation
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/candidates/process-folder` | Trigger CV processing |
| GET | `/api/candidates/list` | List candidates (paginated) |
| GET | `/api/candidates/{id}/full-assessment` | Full assessment |
| GET | `/api/candidates/{id}/missing-info` | Missing info + email |
| POST | `/api/candidates/{id}/send-info-request` | Save email draft |
| POST | `/api/candidates/batch-process` | Batch email generation |
| GET | `/api/candidates/{id}/summary` | Summary report |

---

## Milestone 3 — Full Integrated System, Final Report, Live Demo

### Expected Work and Minimum Demo Expectation (Implemented)

- Complete working web application (React + FastAPI)
- Full implementation of functional modules (preprocessing, analysis, rankings, research, missing info)
- Folder-based CV processing for multiple candidates (UI folder upload + backend processing)
- Candidate-wise tabular outputs (list view + detail tabs)
- Graphical dashboard and comparative views (dashboard + analytics)
- Candidate summary generation (quick profile + summary endpoint)
- Personalized missing-information email drafting (missing info tab + draft view)
- End-to-end integration (frontend <-> backend <-> analysis pipeline)

### Milestone 3 UI Highlights

- Candidate pipeline status (shortlisted / rejected / unreviewed) with filters and actions
- Candidate detail actions for shortlist / reject
- Research publications rendered in tables with rank and quartile columns
- Analytics insights with score, education, and experience distributions
- Processing flow uses folder selection instead of manual path entry
