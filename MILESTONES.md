# Milestones & Feature Tracker

## Overview

The pipeline is broken into 6 milestones, each independently releasable and testable. Each milestone builds on the previous. Milestone 1 is pure local work — no API keys required.

---

## Milestone 0 — Project Bootstrap

**Goal:** Repo is runnable, linted, and CI-green with zero features implemented.

**Issues:**
- [x] `M0-1` Initialize `pyproject.toml` with all dependency groups
- [x] `M0-2` Configure `ruff`, `mypy`, `pytest` in `pyproject.toml`
- [x] `M0-3` Scaffold full folder structure with stub `__init__.py` files
- [x] `M0-4` Create `.env.example` with all required variables documented
- [x] `M0-5` Create `.gitignore` (venv, .env, token.json, state.db, etc.)
- [x] `M0-6` Add GitHub Actions CI workflow (`ci.yml`): lint → type-check → unit tests
- [x] `M0-7` Add GitHub Actions release workflow (`release.yml`): build on tag push
- [x] `M0-8` Add `ISSUE_TEMPLATE` bug report and feature request templates
- [x] `M0-9` Write `scripts/register_device.py` (one-time reMarkable device registration)
- [x] `M0-10` Write `scripts/setup_google_auth.py` (Google OAuth desktop flow)

**Acceptance criteria:**
- `ruff check src/ tests/` exits 0
- `mypy src/` exits 0 (stubs only, no logic yet)
- `pytest tests/unit/ -v` passes (no tests yet = 0 collected, still green)
- CI passes on push to main

---

## Milestone 1 — reMarkable Sync

**Goal:** Authenticate with reMarkable Cloud, list documents, download ZIPs, extract `.rm` files to disk.

**Issues:**
- [x] `M1-1` Implement `config.py` — `pydantic-settings` loading all env vars, validation
- [x] `M1-2` Implement `remarkable/auth.py` — device registration POST, user token renewal POST, `auto_refresh_token` decorator
- [x] `M1-3` Implement `remarkable/client.py` — `RemarkableClient.list_documents()`, `download_zip()`, `upload_zip()`
- [x] `M1-4` Implement `remarkable/sync.py` — incremental sync loop, skip already-processed hashes
- [x] `M1-5` Implement `utils/hashing.py` — SHA-256 hash of `.rm` file bytes
- [x] `M1-6` Implement `utils/retry.py` — `tenacity` decorators + `pybreaker` circuit breaker
- [x] `M1-7` Implement `utils/logging.py` — `structlog` JSON setup with context binding
- [x] `M1-8` Implement `state/db.py` — SQLite init, `is_processed()`, `mark_processed()`, `processed_pages` schema
- [x] `M1-9` Add CLI command `rm-notebooklm sync` (list + download only)
- [x] `M1-10` Implement run-lock in `state/lock.py` — acquire an exclusive
  file lock (`fcntl.flock` on POSIX) at the start of `rm-notebooklm run`,
  release on exit or exception. If lock is already held (previous run still
  executing), log `"pipeline_already_running"` and **exit 0** (not 1 — a
  skip is correct behaviour for a cron/systemd context, not an error).
  Prevents overlapping scheduled invocations from racing on SQLite writes
  or producing duplicate PDF uploads.
- [x] `M1-11` Add `PyYAML>=6.0` to `pyproject.toml` dependencies; add `yaml`
  to `[[tool.mypy.overrides]]` ignore list
- [x] `M1-12` Implement `mapping/models.py` — `MappingEntry` (Pydantic), `MappingsConfig`;
  validate field types, `responses_folder` default `"responses"`,
  optional `notebooklm_path` override
- [x] `M1-13` Implement `mapping/loader.py` — `load_mappings(path: Path) -> list[MappingEntry]`;
  `yaml.safe_load` only (never `yaml.load`); return `[]` if file absent;
  raise `ValidationError` on malformed YAML (hard failure — do not continue silently)
- [x] `M1-14` Add `rm_notebook_mappings_file` field + `_expanded` property to `config.py`
  (follow the `state_db_path` / `state_db_path_expanded` pattern)
- [x] `M1-15` Add `list_folders() -> list[RemarkableDocument]` to `remarkable/client.py` —
  same auth + circuit breaker pattern as `list_documents()`; filters `CollectionType` items
- [x] `M1-16` Implement `mapping/resolver.py` — `ResolvedMapping` dataclass,
  `resolve_mapping_uuids(entry, client)` resolves folder + notebook names to reMarkable UUIDs;
  raises `ValueError` with actionable message on name mismatch
- [x] `M1-17` Wire `notebooklm_nb_id` param into `state/db.py:mark_processed()` —
  column already in schema, INSERT/UPDATE not yet populating it
- [x] `M1-18` Write `docs/notebook-mappings.md` — user-facing YAML schema reference
  (referenced from `.env.example`)
- [x] `M1-19` Tests: `tests/unit/test_mapping_loader.py`, `tests/unit/test_mapping_resolver.py`;
  extend `tests/unit/test_state_db.py` to cover `notebooklm_nb_id` param

**Tests:**
- `tests/unit/test_auth.py` — token refresh logic, decorator behavior, error cases
- `tests/unit/test_state_db.py` — SQLite CRUD, hash deduplication
- `tests/integration/test_remarkable_api.py` — VCR cassettes for list/download/upload endpoints
  - Record cassettes with `--vcr-record=all` once, commit, run with `--vcr-record=none` in CI

**Acceptance criteria:**
- `rm-notebooklm sync --dry-run` lists documents without downloading
- Token auto-refreshes on 401 (covered by VCR test)
- SHA-256 dedup prevents re-downloading unchanged documents
- Invoking `rm-notebooklm run` while a previous run is in progress logs
  `"pipeline_already_running"` and exits 0 without side effects
- `~/.rm_notebooklm/mappings.yaml` with one entry loads and validates without error
- Missing `mappings.yaml` → `load_mappings()` returns `[]`; malformed YAML → exit 1
- `list_folders()` returns only `CollectionType` items
- `mark_processed()` correctly stores `notebooklm_nb_id` in `processed_pages`

---

## Milestone 2 — .rm Parsing and Text Extraction

**Goal:** Parse downloaded `.rm` files, route typed text to direct extraction and handwriting to OCR preprocessing.

**Issues:**
- [x] `M2-1` Implement `parsing/rm_parser.py` — `rmscene.read_tree()` wrapper, page type detection (`typed` / `handwriting` / `blank`)
- [x] `M2-2` Implement `parsing/extractor.py` — direct text extraction from `RootTextBlock` / `CrdtSequence`
- [x] `M2-3` Implement `parsing/preprocessor.py` — PIL pipeline: grayscale convert, crop toolbar+margins, contrast boost, resize ≤1568px, save as PNG
- [x] `M2-4` Integrate `rmc` rendering — call `rmc -t svg page.rm` → convert SVG to PNG
- [x] `M2-5` Add blank page detection — skip if no `SceneLineItemBlock` and no `RootTextBlock`

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
The primary deployment target is an always-on machine (home server, Raspberry
Pi, or VPS) running a systemd timer. `rm-notebooklm run` is invoked on a
schedule — the user's only interaction is writing on the reMarkable tablet.

**Issues:**
- [ ] `M6-1` Implement full `cli.py` — commands: `sync`, `process`, `upload`, `run` (all stages), `status`
- [ ] `M6-2` Add `--dry-run` flag to all mutating commands
- [ ] `M6-3` Add `--notebook-filter` to target specific reMarkable notebooks
- [ ] `M6-4` Add `--since` flag for date-based incremental sync (limits first-run scope)
- [ ] `M6-5` Implement `rm-notebooklm status` — show last sync time, pending pages, SQLite stats
- [ ] `M6-6a` Write `systemd/rm-notebooklm.service` — `Type=oneshot`, `ExecStart` targets
  venv Python, `EnvironmentFile=/etc/rm-notebooklm/env`
- [ ] `M6-6b` Write `systemd/rm-notebooklm.timer` — `OnCalendar=*:0/10` (every 10 min),
  `Persistent=true` (fires missed runs after sleep/reboot), `Unit=rm-notebooklm.service`
- [ ] `M6-6c` Write `docs/deployment/systemd.md` — installation, credential placement,
  log viewing via `journalctl -u rm-notebooklm`
- [ ] `M6-6d` Write `Dockerfile` — multi-stage build, codifies two-phase rmscene install
  (see `docs/solutions/build-errors/rmapi-rmscene-no-deps-install.md`), `CMD ["rm-notebooklm", "run"]`
- [ ] `M6-6e` Write `docker-compose.yml` — bind-mounts credential and state directories,
  env-file injection; external cron calls `docker run rm-notebooklm run`
- [ ] `M6-6f` Write `docs/deployment/docker.md` — host cron + docker run pattern,
  bind-mount layout, Raspberry Pi (arm64) build instructions
- [ ] `M6-6g` Write `docs/deployment/headless-credentials.md`:
  - How to set up Google service account JSON key (replaces desktop OAuth flow)
    for Paths A and B in unattended server deployments
  - Explicit note: **Path A (cookie-based `notebooklm-py`) cannot be used in
    any scheduled/daemon deployment** — cookies expire every 1–2 weeks with
    no automated renewal path
  - Path C (`GEMINI_API_KEY`) is recommended for server deployments — API key
    never expires, no OAuth required
- [ ] `M6-7` Add Prometheus metrics export (optional, feature flag)
- [ ] `M6-8` Write `docs/setup.md` — complete auth setup guide (interactive/desktop path)
- [ ] `M6-9` Write `docs/architecture.md` — pipeline diagram + paths A/B/C decision tree

**Exit code contract (required for systemd integration):**
- `0` — success, including "no new pages to process" (this is normal, not an error)
- `1` — hard failure (credentials invalid, `mappings.yaml` missing, unrecoverable error)
- `75` (EX_TEMPFAIL) — transient failure (reMarkable API unreachable, rate limited)

**Tests:**
- `tests/e2e/test_full_pipeline.py` — opt-in (`-m e2e --run-e2e`), requires `.env` with real credentials
  - Uploads a known test document to reMarkable
  - Runs full pipeline
  - Asserts response PDF appears in document list
  - Cleans up test documents

**Acceptance criteria:**
- `rm-notebooklm run` invoked by a systemd timer at 10-minute intervals completes
  without errors and produces zero duplicate PDF uploads across 100 consecutive
  invocations on an unchanged reMarkable notebook
- `rm-notebooklm run` invoked while a previous run is in progress exits 0
  without producing side effects (run-lock from M1-10)
- `rm-notebooklm status` shows accurate sync state
- All unit + integration tests pass in CI with zero live network calls

---

## Milestone 6B — GitHub Actions Deployment (Experimental, Optional)

**Goal:** Provide a zero-hardware "free tier" automated path using GitHub Actions
scheduled workflows and a Gist-backed state store. Explicitly experimental and
architecturally inferior to the systemd/Docker path. Requires no home server.

**Constraint:** Path A (cookie-based) is incompatible with this milestone entirely.
Path B requires service account credentials (not desktop OAuth). Path C is the
recommended path here.

**Issues:**
- [ ] `M6B-1` Extract `StateBackend` ABC from `state/db.py`:
  `is_processed()`, `mark_processed()`, `get_stats()`, `close()`
- [ ] `M6B-2` Rename existing SQLite implementation to `SQLiteBackend`
  (zero behaviour change for all existing code and tests)
- [ ] `M6B-3` Implement `GistBackend` — serialise processed-pages set as a JSON
  array of `(page_id, content_hash)` tuples in a private GitHub Gist; read on
  init, write on each `mark_processed()` call; handle Gist API rate limits
  gracefully (log + continue, never crash)
- [ ] `M6B-4` Add `STATE_BACKEND=sqlite|gist` to `config.py` and `.env.example`;
  factory in `state/__init__.py`
- [ ] `M6B-5` Add `.github/workflows/pipeline.yml` scheduled workflow —
  `schedule: cron '*/15 * * * *'`, reads all secrets from GitHub Actions
  environment, no persistent runner filesystem assumed
- [ ] `M6B-6` Write `docs/deployment/github-actions.md` — service account setup
  for Google APIs, secret configuration, acknowledged limitations
- [ ] `M6B-7` Documented limitations: no atomicity guarantee on concurrent runs,
  1 MB practical Gist state limit, Path A incompatible, `rmc` GitHub install
  adds ~60s to every Actions run

**Acceptance criteria:**
- Pipeline runs on schedule in GitHub Actions without producing duplicate uploads
  when the Gist state is intact
- Pipeline handles Gist read failure gracefully: treats as empty state, logs
  warning — does not crash
- All existing unit tests pass against `GistBackend` via in-memory mock
- `SQLiteBackend` behaviour is byte-for-byte identical to current behaviour

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
| Overlapping pipeline runs (timer fires mid-OCR) | Medium | Run-lock in `state/lock.py` (M1-10) exits 0 cleanly |
| Headless Google OAuth for unattended servers | High | Use Path C (`GEMINI_API_KEY`) for server deploys; document service account migration in M6-6g |
| First run processes entire notebook history | Medium | `--since` flag (M6-4) and `--max-pages` flag limit first-run scope |
| Path A cookie expiry on home server | Certain | Path A cannot be used in any scheduled deployment; default and document Path C |
