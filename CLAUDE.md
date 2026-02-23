# reMarkable → NotebookLM Pipeline: Claude Code Context

## Project Overview

This project automates a pipeline that:
1. Syncs handwritten notes from a **reMarkable 2** tablet via cloud API
2. Parses `.rm` binary files, extracts typed text directly, OCRs handwriting via vision LLM
3. Uploads processed content to **NotebookLM** (or Gemini API with grounding) as sources
4. Generates AI responses as PDFs formatted for reMarkable 2 display dimensions
5. Uploads response PDFs back to the reMarkable device

**Critical constraint:** The official NotebookLM Enterprise API (v1alpha) has no chat/query endpoint. Architecture accounts for three paths — see `docs/architecture.md`.

---

## Repository Layout

```
remarkable-notebooklm/
├── CLAUDE.md                    # This file — Claude Code context
├── MILESTONES.md                # Feature milestones and issue tracker
├── pyproject.toml               # Single source of truth for deps + tooling
├── .env.example                 # Required environment variables (no secrets)
├── .github/
│   ├── workflows/
│   │   ├── ci.yml               # Lint, type-check, test on every PR
│   │   └── release.yml          # Build + publish on tag push
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
├── docs/
│   ├── architecture.md          # Pipeline diagram + API paths A/B/C
│   ├── setup.md                 # Auth setup: reMarkable, Google, NotebookLM
│   └── blueprint.md             # Original technical blueprint (source of truth)
├── src/
│   └── rm_notebooklm/           # Main package (importable as `rm_notebooklm`)
│       ├── __init__.py
│       ├── cli.py               # Typer-based CLI entry point
│       ├── config.py            # Pydantic Settings — loads from env/.env
│       ├── remarkable/
│       │   ├── __init__.py
│       │   ├── auth.py          # Device registration + token refresh
│       │   ├── client.py        # RemarkableClient: list/download/upload docs
│       │   └── sync.py          # Incremental sync with SQLite state tracking
│       ├── parsing/
│       │   ├── __init__.py
│       │   ├── rm_parser.py     # rmscene wrapper: detect stroke vs typed text
│       │   ├── extractor.py     # Direct text extraction from RootTextBlock
│       │   └── preprocessor.py  # PIL image preprocessing for OCR
│       ├── ocr/
│       │   ├── __init__.py
│       │   ├── base.py          # Abstract OCRProvider interface
│       │   ├── gemini.py        # Gemini 2.5 Flash OCR implementation
│       │   ├── openai.py        # GPT-4o / GPT-4o-mini OCR implementation
│       │   └── claude.py        # Claude Sonnet/Haiku OCR implementation
│       ├── notebooklm/
│       │   ├── __init__.py
│       │   ├── enterprise.py    # Official NotebookLM Enterprise API (Path B)
│       │   ├── unofficial.py    # notebooklm-py cookie-based client (Path A)
│       │   └── drive.py         # Google Drive intermediary layer
│       ├── gemini/
│       │   ├── __init__.py
│       │   └── grounding.py     # Gemini API with doc grounding (Path C)
│       ├── pdf/
│       │   ├── __init__.py
│       │   ├── generator.py     # fpdf2-based PDF with reMarkable 2 dimensions
│       │   └── constants.py     # RM2 page dimensions, margins, typography
│       ├── state/
│       │   ├── __init__.py
│       │   └── db.py            # SQLite state tracking (processed_pages table)
│       └── utils/
│           ├── __init__.py
│           ├── retry.py         # tenacity decorators + pybreaker circuit breaker
│           ├── hashing.py       # SHA-256 content hashing helpers
│           └── logging.py       # structlog JSON logging setup
├── tests/
│   ├── conftest.py              # Shared fixtures, VCR cassette config
│   ├── fixtures/
│   │   ├── cassettes/           # VCR HTTP cassettes (committed)
│   │   └── rm_files/            # Sample .rm files from rmscene test suite
│   ├── unit/
│   │   ├── test_auth.py
│   │   ├── test_rm_parser.py
│   │   ├── test_preprocessor.py
│   │   ├── test_ocr_quality.py  # jiwer CER/WER assertions
│   │   ├── test_pdf_generator.py
│   │   └── test_state_db.py
│   ├── integration/
│   │   ├── test_remarkable_api.py   # VCR-recorded
│   │   ├── test_drive_upload.py     # VCR-recorded
│   │   └── test_notebooklm_api.py   # VCR-recorded
│   └── e2e/
│       └── test_full_pipeline.py    # Requires real credentials (opt-in)
└── scripts/
    ├── register_device.py       # One-time reMarkable device registration
    └── setup_google_auth.py     # Google OAuth desktop flow setup
```

---

## Environment Variables

All config is loaded via `src/rm_notebooklm/config.py` using `pydantic-settings`. Copy `.env.example` to `.env`.

```bash
# reMarkable
RM_DEVICE_TOKEN=          # Permanent JWT from device registration
RM_USER_TOKEN=            # Short-lived JWT (auto-refreshed if empty)

# OCR Provider (pick one)
OCR_PROVIDER=gemini       # gemini | openai | claude
GEMINI_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# NotebookLM path (A, B, or C)
NOTEBOOKLM_PATH=C         # A=unofficial | B=enterprise | C=gemini-grounding

# Path A: notebooklm-py (unofficial)
NOTEBOOKLM_AUTH_JSON=     # Path to ~/.notebooklm/storage_state.json

# Path B: Enterprise API
NOTEBOOKLM_PROJECT_NUMBER=
NOTEBOOKLM_LOCATION=us-central1
NOTEBOOKLM_ENDPOINT_LOCATION=us-central1

# Path C: Gemini grounding (reuses GEMINI_API_KEY)
GCS_BUCKET_NAME=          # GCS bucket for document uploads

# Google Drive (Paths A and B)
GOOGLE_CREDENTIALS_JSON=credentials.json   # OAuth client secrets
GOOGLE_TOKEN_JSON=token.json               # Auto-managed token cache
GOOGLE_DRIVE_FOLDER_ID=                    # Optional target folder

# State
STATE_DB_PATH=~/.rm_notebooklm/state.db
LOG_LEVEL=INFO
LOG_FORMAT=json           # json | text
```

---

## Key Technical Decisions

### reMarkable Cloud API
- **Library:** `rm-api` v1.1.1 (supports sync15 protocol; `rmapy` does NOT)
- **Auth:** Two-token JWT system; device token is permanent, user token refreshes per session
- **API typo:** Field is `VissibleName` (not `VisibleName`) — this is in the real API

### .rm File Parsing
- **Library:** `rmscene` v0.7.0 for v6 format (firmware 3.x+)
- **Decision tree:**
  - `RootTextBlock` present + no `SceneLineItemBlock` → direct text extraction, skip OCR
  - `SceneLineItemBlock` present → render to PNG → vision LLM OCR
  - Empty scene tree → skip (blank page)
- **Renderer:** `rmc` v0.3.0 for SVG/PNG output

### OCR
- Default provider: **Gemini 2.5 Flash** ($0.002/page, free tier for dev)
- Pre-resize images to ≤1568px on long edge before sending to Claude (prevents server-side resize)
- Image format: PNG (lossless), grayscale, crop 120px left toolbar + 40px margins
- Abstract `OCRProvider` base class — swap providers without changing pipeline code

### NotebookLM Integration
- **Default path: C (Gemini with grounding)** — fully official, no cookie fragility
- Path A (`notebooklm-py`): cookies expire every 1-2 weeks; only for prototyping
- Path B (Enterprise): requires GCP project + Discovery Engine API; no chat endpoint

### PDF Output
- **Library:** `fpdf2` (zero deps, handles pagination)
- **Page size:** 447.3 × 596.4 PDF points (1404×1872px @ 226 DPI)
- **Left margin:** 72pt (1 inch) — accounts for reMarkable toolbar
- **Typography:** min 12pt font, 1.3–1.5× line spacing, embed all fonts
- **Max file size:** 100MB

### State Management
- **SQLite** at `STATE_DB_PATH` tracks processed pages by SHA-256 hash
- Prevents duplicate OCR/upload on re-sync
- Must fetch latest server version before upload (reMarkable requires `Version = server_version + 1`)

### Error Handling
- `tenacity`: exponential backoff with jitter for all external API calls
- `pybreaker`: circuit breaker (fail_max=5, reset_timeout=60) for reMarkable API
- `auto_refresh_token` decorator pattern for both reMarkable and Google auth
- `structlog`: JSON structured logging with per-page/notebook context binding

---

## Development Setup

```bash
# Python 3.10+ required (rmscene constraint)
python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"

# One-time device registration
python scripts/register_device.py

# One-time Google OAuth
python scripts/setup_google_auth.py
```

### Running Tests

```bash
# Unit tests only (no credentials needed)
pytest tests/unit/ -v

# Integration tests (uses VCR cassettes — no live network)
pytest tests/integration/ -v --vcr-record=none

# OCR quality tests (requires OCR provider API key)
pytest tests/unit/test_ocr_quality.py -v -m ocr

# Full E2E (requires real credentials, writes to reMarkable + NotebookLM)
pytest tests/e2e/ -v -m e2e --run-e2e
```

### Code Quality

```bash
ruff check src/ tests/          # Linting
ruff format src/ tests/         # Formatting
mypy src/                       # Type checking
pytest --cov=rm_notebooklm      # Coverage
```

---

## Pipeline Flow (Happy Path)

```
reMarkable Cloud
      |
      | rm-api: list docs with VissibleName, BlobURLGet
      v
   Download ZIP → extract .rm files
      |
      | rmscene: read_tree() per page
      v
   Route: typed text → direct extract
          handwriting → preprocess PNG → vision LLM OCR
          blank → skip
      |
      | Structured text per page
      v
   NotebookLM (Path A/B) or Gemini Grounding (Path C)
      | Upload source
      | Query for summary/response
      v
   AI response text
      |
      | fpdf2: generate PDF at 447.3×596.4pt
      v
   Upload PDF ZIP to reMarkable Cloud
      |
      | Update SQLite state (page_id, content_hash, processed_at)
      v
   Done — response appears in reMarkable document list
```

---

## Critical Library Versions (pin these)

| Library | Version | Notes |
|---------|---------|-------|
| `rm-api` | 1.1.1 | sync15 support; replaces `rmapy` |
| `rmscene` | 0.7.0 | v6 .rm format (firmware 3.x+) |
| `rmc` | 0.3.0 | install from GitHub for latest |
| `fpdf2` | latest | PDF generation |
| `notebooklm-py` | 0.3.0 | Path A only; cookie-based, fragile |
| `google-api-python-client` | 2.189.0 | Drive API |
| `google-auth-oauthlib` | 1.31.0 | OAuth flow |
| `tenacity` | latest | Retry with backoff |
| `pybreaker` | latest | Circuit breaker |
| `structlog` | latest | Structured logging |
| `jiwer` | 3.x | OCR quality metrics (CER/WER) |
| `Pillow` | latest | Image preprocessing |
| `pydantic-settings` | latest | Config from env |
| `typer` | latest | CLI |

---

## What NOT to Do

- Do not use `rmapy` — it does not support sync15 and will fail on migrated accounts
- Do not use JPEG for OCR images — PNG preserves stroke edges
- Do not upscale reMarkable images — 226 DPI is sufficient for vision LLMs
- Do not binarize images before OCR — LLMs handle grayscale gradients better
- Do not commit `.env`, `token.json`, `credentials.json`, or `state.db`
- Do not assume NotebookLM Enterprise chat works via API — it does not
- Do not use `rmapy` — mentioned twice because it's the most common mistake
