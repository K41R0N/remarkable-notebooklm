# Milestones & Feature Tracker

## Overview

The pipeline is broken into 6 milestones, each independently releasable and testable. Each milestone builds on the previous. Milestone 1 is pure local work — no API keys required.

---

## Milestone 0 — Project Bootstrap

**Goal:** Repo is runnable, linted, and CI-green with zero features implemented.

**Issues:**
- [ ] `M0-1` Initialize `pyproject.toml` with all dependency groups
- [ ] `M0-2` Configure `ruff`, `mypy`, `pytest` in `pyproject.toml`
- [ ] `M0-3` Scaffold full folder structure with stub `__init__.py` files
- [ ] `M0-4` Create `.env.example` with all required variables documented
- [ ] `M0-5` Create `.gitignore` (venv, .env, token.json, state.db, etc.)
- [ ] `M0-6` Add GitHub Actions CI workflow (`ci.yml`): lint → type-check → unit tests
- [ ] `M0-7` Add GitHub Actions release workflow (`release.yml`): build on tag push
- [ ] `M0-8` Add `ISSUE_TEMPLATE` bug report and feature request templates
- [ ] `M0-9` Write `scripts/register_device.py` (one-time reMarkable device registration)
- [ ] `M0-10` Write `scripts/setup_google_auth.py` (Google OAuth desktop flow)

**Acceptance criteria:**
- `ruff check src/ tests/` exits 0
- `mypy src/` exits 0 (stubs only, no logic yet)
- `pytest tests/unit/ -v` passes (no tests yet = 0 collected, still green)
- CI passes on push to main

---

## Milestone 1 — reMarkable Sync

**Goal:** Authenticate with reMarkable Cloud, list documents, download ZIPs, extract `.rm` files to disk.

**Issues:**
- [ ] `M1-1` Implement `config.py` — `pydantic-settings` loading all env vars, validation
- [ ] `M1-2` Implement `remarkable/auth.py` — device registration POST, user token renewal POST, `auto_refresh_token` decorator
- [ ] `M1-3` Implement `remarkable/client.py` — `RemarkableClient.list_documents()`, `download_zip()`, `upload_zip()`
- [ ] `M1-4` Implement `remarkable/sync.py` — incremental sync loop, skip already-processed hashes
- [ ] `M1-5` Implement `utils/hashing.py` — SHA-256 hash of `.rm` file bytes
- [ ] `M1-6` Implement `utils/retry.py` — `tenacity` decorators + `pybreaker` circuit breaker
- [ ] `M1-7` Implement `utils/logging.py` — `structlog` JSON setup with context binding
- [ ] `M1-8` Implement `state/db.py` — SQLite init, `is_processed()`, `mark_processed()`, `processed_pages` schema
- [ ] `M1-9` Add CLI command `rm-notebooklm sync` (list + download only)

**Tests:**
- `tests/unit/test_auth.py` — token refresh logic, decorator behavior, error cases
- `tests/unit/test_state_db.py` — SQLite CRUD, hash deduplication
- `tests/integration/test_remarkable_api.py` — VCR cassettes for list/download/upload endpoints
  - Record cassettes with `--vcr-record=all` once, commit, run with `--vcr-record=none` in CI

**Acceptance criteria:**
- `rm-notebooklm sync --dry-run` lists documents without downloading
- Token auto-refreshes on 401 (covered by VCR test)
- SHA-256 dedup prevents re-downloading unchanged documents

---

## Milestone 2 — .rm Parsing and Text Extraction

**Goal:** Parse downloaded `.rm` files, route typed text to direct extraction and handwriting to OCR preprocessing.

**Issues:**
- [ ] `M2-1` Implement `parsing/rm_parser.py` — `rmscene.read_tree()` wrapper, page type detection (`typed` / `handwriting` / `blank`)
- [ ] `M2-2` Implement `parsing/extractor.py` — direct text extraction from `RootTextBlock` / `CrdtSequence`
- [ ] `M2-3` Implement `parsing/preprocessor.py` — PIL pipeline: grayscale convert, crop toolbar+margins, contrast boost, resize ≤1568px, save as PNG
- [ ] `M2-4` Integrate `rmc` rendering — call `rmc -t svg page.rm` → convert SVG to PNG
- [ ] `M2-5` Add blank page detection — skip if no `SceneLineItemBlock` and no `RootTextBlock`

**Tests:**
- `tests/unit/test_rm_parser.py` — fixture `.rm` files from `rmscene` test suite, assert correct routing
- `tests/unit/test_preprocessor.py` — assert output is grayscale PNG, dimensions ≤1568px, no toolbar region
- `tests/fixtures/rm_files/` — commit sample `.rm` files covering: typed-only, handwriting-only, mixed, blank

**Acceptance criteria:**
- Typed pages produce text without calling any OCR API
- Handwriting pages produce PNG ≤1568px long edge
- Blank pages produce `None` and are logged as skipped
- `cer()` on known typed-text samples = 0.0 (exact extraction)

---

## Milestone 3 — Vision LLM OCR

**Goal:** Send preprocessed PNGs to a vision LLM and return transcribed text, with quality gates.

**Issues:**
- [ ] `M3-1` Define `ocr/base.py` — abstract `OCRProvider` with `transcribe(image: bytes) -> str`
- [ ] `M3-2` Implement `ocr/gemini.py` — Gemini 2.5 Flash with exact system prompt from blueprint
- [ ] `M3-3` Implement `ocr/openai.py` — GPT-4o and GPT-4o-mini variants
- [ ] `M3-4` Implement `ocr/claude.py` — Claude Sonnet/Haiku with pre-resize guard
- [ ] `M3-5` Add provider factory in `ocr/__init__.py` — select via `OCR_PROVIDER` env var
- [ ] `M3-6` Apply `tenacity` retry (5 attempts, exp backoff + jitter) to all OCR calls
- [ ] `M3-7` Add cost estimation logging per page (token count × rate)

**Tests:**
- `tests/unit/test_ocr_quality.py` (`-m ocr`, requires API key)
  - Parametrize over known handwriting samples in `tests/fixtures/rm_files/`
  - Assert `cer(expected, result) < 0.10` and `wer(expected, result) < 0.15`
  - Separate `expected_text/` files committed alongside fixtures

**Acceptance criteria:**
- All three providers accept the same `bytes` input and return `str`
- Swapping `OCR_PROVIDER` env var changes provider without code changes
- OCR quality tests pass against sample fixtures with all three providers

---

## Milestone 4 — NotebookLM / Gemini Integration

**Goal:** Upload processed text as a source, query for an AI-grounded response. Three paths supported.

**Sub-milestone 4A — Gemini Grounding (Path C, default):**
- [ ] `M4A-1` Implement `gemini/grounding.py` — upload text to GCS, call Gemini API with document grounding
- [ ] `M4A-2` Add GCS bucket creation/reuse logic
- [ ] `M4A-3` Return structured response from Gemini (summary + key points)

**Sub-milestone 4B — NotebookLM Enterprise (Path B):**
- [ ] `M4B-1` Implement `notebooklm/enterprise.py` — create notebook, upload source via `sources:uploadFile`
- [ ] `M4B-2` Implement `notebooklm/drive.py` — upload Google Doc, return `documentId` for `sources:batchCreate`
- [ ] `M4B-3` Note: no chat endpoint; return notebook URL only

**Sub-milestone 4C — Unofficial notebooklm-py (Path A):**
- [ ] `M4C-1` Implement `notebooklm/unofficial.py` — `NotebookLMClient.from_storage()`, add source, `chat.ask()`
- [ ] `M4C-2` Add cookie expiry detection and helpful error message with re-auth instructions

**Shared:**
- [ ] `M4-1` Define response schema (`dataclasses` or `pydantic`) — `AIResponse(text: str, source_ids: list[str], notebook_id: str | None)`
- [ ] `M4-2` Add `NOTEBOOKLM_PATH` routing in CLI

**Tests:**
- `tests/integration/test_notebooklm_api.py` — VCR cassettes for Enterprise API CRUD
- `tests/integration/test_drive_upload.py` — VCR cassettes for Drive upload + share
- Path A: mock `NotebookLMClient` via `unittest.mock` (no VCR — library uses internal httpx)

**Acceptance criteria:**
- Path C (default) returns a non-empty `AIResponse.text` grounded in uploaded source
- Path B creates notebook and source, returns notebook URL
- Path A returns grounded chat response (flagged as fragile in docs)

---

## Milestone 5 — PDF Generation and Upload

**Goal:** Convert AI response text to a reMarkable-formatted PDF and upload back to the device.

**Issues:**
- [ ] `M5-1` Implement `pdf/constants.py` — all dimension/margin/typography constants
- [ ] `M5-2` Implement `pdf/generator.py` — `RemarkablePDF` class with header/footer, auto-pagination, Markdown rendering
- [ ] `M5-3` Handle long responses: section headers, bullet points, code blocks (monospace)
- [ ] `M5-4` Build upload ZIP structure (`{uuid}.content`, `{uuid}.pagedata`, `{uuid}/{page}.rm`)
- [ ] `M5-5` Implement `RemarkableClient.upload_pdf()` — 3-step upload (request → PUT blob → update-status)
- [ ] `M5-6` Enforce 100MB file size limit with truncation + warning

**Tests:**
- `tests/unit/test_pdf_generator.py`
  - Assert output file is valid PDF (use `pypdf` for verification)
  - Assert page size = 447.3 × 596.4 pts (±0.5 tolerance)
  - Assert left margin ≥ 72pt
  - Assert minimum font size ≥ 12pt
  - Assert file size < 100MB for 10,000 word input

**Acceptance criteria:**
- PDF opens correctly on reMarkable 2 (manual verification step)
- All text readable without horizontal scrolling
- Document appears in reMarkable document list after upload

---

## Milestone 6 — Full Pipeline CLI and Polish

**Goal:** End-to-end CLI, scheduling, monitoring, and production hardening.

**Issues:**
- [ ] `M6-1` Implement full `cli.py` — commands: `sync`, `process`, `upload`, `run` (all stages), `status`
- [ ] `M6-2` Add `--dry-run` flag to all mutating commands
- [ ] `M6-3` Add `--notebook-filter` to target specific reMarkable notebooks
- [ ] `M6-4` Add `--since` flag for date-based incremental sync
- [ ] `M6-5` Implement `rm-notebooklm status` — show last sync time, pending pages, SQLite stats
- [ ] `M6-6` Add systemd service unit file for scheduled runs
- [ ] `M6-7` Add Prometheus metrics export (optional, feature flag)
- [ ] `M6-8` Write `docs/setup.md` — complete auth setup guide
- [ ] `M6-9` Write `docs/architecture.md` — pipeline diagram + paths A/B/C decision tree

**Tests:**
- `tests/e2e/test_full_pipeline.py` — opt-in (`-m e2e --run-e2e`), requires `.env` with real credentials
  - Uploads a known test document to reMarkable
  - Runs full pipeline
  - Asserts response PDF appears in document list
  - Cleans up test documents

**Acceptance criteria:**
- `rm-notebooklm run` completes without errors on a real reMarkable device
- `rm-notebooklm status` shows accurate sync state
- All unit + integration tests pass in CI with zero live network calls

---

## Test Matrix

| Test Suite | Location | Credentials | CI |
|-----------|----------|-------------|-----|
| Unit | `tests/unit/` | None | Always |
| Integration | `tests/integration/` | VCR cassettes | Always (`--vcr-record=none`) |
| OCR quality | `tests/unit/test_ocr_quality.py` | API key (`-m ocr`) | Optional (manual) |
| E2E | `tests/e2e/` | Real credentials (`-m e2e`) | Never (manual only) |

---

## Issue Labels

- `milestone:0` through `milestone:6`
- `type:feature`, `type:bug`, `type:test`, `type:docs`, `type:infra`
- `priority:critical`, `priority:high`, `priority:medium`, `priority:low`
- `path:A`, `path:B`, `path:C` — NotebookLM integration path
- `blocked` — waiting on external API availability

---

## Known Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `notebooklm-py` RPC breakage (Path A) | High | Default to Path C; document Path A as experimental |
| reMarkable sync15 API changes | Medium | Pin `rm-api==1.1.1`; integration tests will catch |
| Cookie expiry in CI for Path A | Certain | Use Path C in CI; Path A for local dev only |
| Claude image resize causing quality loss | Medium | Pre-resize to ≤1568px in `preprocessor.py` |
| `VissibleName` typo correction by reMarkable | Low | Watch `rm-api` changelog |
