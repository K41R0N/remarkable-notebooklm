---
title: "feat: Milestone 1 — reMarkable Sync"
type: feat
status: completed
date: 2026-02-23
---

# feat: Milestone 1 — reMarkable Sync

## Overview

Implement the first functional milestone of the pipeline: authenticate with the reMarkable Cloud, list documents, download ZIPs containing `.rm` files, and track processed state in SQLite. When complete, `rm-notebooklm sync --dry-run` will list documents and `rm-notebooklm sync` will download new/changed ones incrementally.

Milestone 0 (project bootstrap) is **fully complete** — the scaffold, CI, and tooling are all in place. This milestone fills in every `NotImplementedError` stub that is tagged "Milestone 1", plus enables the corresponding skipped unit and integration tests.

---

## Current State

All files exist with correct module structure and function signatures. The following are **already implemented** and do not need to be changed:

| File | Status |
|------|--------|
| `config.py` | ✅ Complete — pydantic-settings, all env vars, validator |
| `utils/hashing.py` | ✅ Complete — `hash_file()`, `hash_bytes()` |
| `remarkable/auth.py` | ⚠️ Partial — `auto_refresh_token` decorator done; `register_device()` and `refresh_user_token()` are stubs |
| `remarkable/client.py` | ⚠️ Partial — `RemarkableDocument` dataclass and `__init__`/`_refresh_user_token` done; `list_documents()` and `download_zip()` are stubs |
| `state/db.py` | ⚠️ Partial — `__init__`, `_init_db`, `_connect` done; `is_processed()` and `mark_processed()` are stubs |
| `utils/logging.py` | ❌ Stub — both functions raise `NotImplementedError` |
| `utils/retry.py` | ❌ Stub — both functions raise `NotImplementedError`; `remarkable_breaker = None` |
| `remarkable/sync.py` | ❌ Stub — `SyncManager.sync()` raises `NotImplementedError` |
| `cli.py` | ❌ Stub — `sync` command raises `NotImplementedError` |

Tests that are currently skipped and will be enabled:
- `tests/unit/test_auth.py` → `test_token_refresh_on_401`
- `tests/unit/test_state_db.py` → all four tests
- `tests/integration/test_remarkable_api.py` → `test_list_documents_returns_docs`, `test_download_zip_saves_file`

---

---

## Technical Considerations

### `utils/logging.py`

Use `structlog` with `structlog.stdlib` processors. Configure two modes:
- `json` (production): `JSONRenderer` with timestamped entries
- `text` (development): `ConsoleRenderer` with colors

```python
# src/rm_notebooklm/utils/logging.py

import logging
import structlog

def configure_logging(level: str = "INFO", fmt: str = "json") -> None:
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    if fmt == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))

def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
```

### `utils/retry.py`

Use `tenacity` for backoff and `pybreaker` for circuit breaking. Initialize a module-level `remarkable_breaker` instance so it is shared across all `RemarkableClient` calls in the same process.

```python
# src/rm_notebooklm/utils/retry.py

from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type
import httpx, requests, pybreaker

def make_retry_decorator(max_attempts=5, initial_wait=1.0, max_wait=60.0, jitter=2.0):
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=initial_wait, max=max_wait, jitter=jitter),
        retry=retry_if_exception_type((requests.HTTPError, httpx.HTTPStatusError, ConnectionError)),
        reraise=True,
    )

def make_circuit_breaker(fail_max=5, reset_timeout=60, success_threshold=3):
    return pybreaker.CircuitBreaker(
        fail_max=fail_max,
        reset_timeout=reset_timeout,
        success_threshold=success_threshold,
    )

# Module-level singleton — shared across all RemarkableClient instances
remarkable_breaker = make_circuit_breaker()
```

### `state/db.py` — `is_processed` and `mark_processed`

`is_processed` must check **both** `page_id` AND `content_hash` — a matching page_id with a different hash means the page has been edited and needs reprocessing.

```python
# src/rm_notebooklm/state/db.py  (additions only)

def is_processed(self, page_id: str, content_hash: str) -> bool:
    with self._connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM processed_pages WHERE page_id = ? AND content_hash = ?",
            (page_id, content_hash),
        ).fetchone()
    return row is not None

def mark_processed(self, *, page_id, notebook_id, content_hash, ocr_text=None, version):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    with self._connect() as conn:
        conn.execute(
            """INSERT INTO processed_pages
               (page_id, notebook_id, content_hash, ocr_text, processed_at, version)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(page_id) DO UPDATE SET
                 content_hash=excluded.content_hash,
                 ocr_text=excluded.ocr_text,
                 processed_at=excluded.processed_at,
                 version=excluded.version
            """,
            (page_id, notebook_id, content_hash, ocr_text, now, version),
        )
```

### `remarkable/auth.py` — HTTP implementation

Both endpoints return a plain-text JWT (not JSON). Use `requests` directly; the `rm-api` library handles higher-level sync15 protocol calls but these registration endpoints are raw HTTP.

```python
# src/rm_notebooklm/remarkable/auth.py  (additions only)

import uuid, requests

def register_device(one_time_code: str) -> str:
    resp = requests.post(
        DEVICE_REGISTRATION_URL,
        headers={"Authorization": "Bearer ", "Content-Type": "application/json"},
        json={"code": one_time_code, "deviceDesc": "desktop-linux", "deviceID": str(uuid.uuid4())},
        timeout=30,
    )
    if resp.status_code != 200:
        raise AuthenticationError(f"Registration failed: {resp.status_code} {resp.text}")
    return resp.text.strip()

def refresh_user_token(device_token: str) -> str:
    resp = requests.post(
        USER_TOKEN_URL,
        headers={"Authorization": f"Bearer {device_token}"},
        timeout=30,
    )
    if resp.status_code != 200:
        raise AuthenticationError(f"Token refresh failed: {resp.status_code} {resp.text}")
    return resp.text.strip()
```

### `remarkable/client.py` — `list_documents` and `download_zip`

- Wrap calls in the `remarkable_breaker` circuit breaker
- Apply `@auto_refresh_token(max_retries=1)` to `list_documents`
- `list_documents` uses `withBlob=true` query param to get signed GCS URLs
- `download_zip` fetches the `BlobURLGet` URL — no auth header needed (signed URL)
- Map the `VissibleName` typo from the API response correctly

```python
# src/rm_notebooklm/remarkable/client.py  (additions only)

import requests
from rm_notebooklm.remarkable.auth import AuthenticationError, auto_refresh_token
from rm_notebooklm.utils.retry import remarkable_breaker

# In RemarkableClient:

@auto_refresh_token(max_retries=1)
def list_documents(self) -> list[RemarkableDocument]:
    def _call():
        resp = requests.get(
            LIST_URL,
            headers={"Authorization": f"Bearer {self._user_token}"},
            params={"withBlob": "true"},
            timeout=30,
        )
        if resp.status_code == 401:
            raise AuthenticationError("User token expired")
        resp.raise_for_status()
        return resp.json()

    items = remarkable_breaker.call(_call)
    return [
        RemarkableDocument(
            id=item["ID"],
            vissible_name=item.get("VissibleName", ""),
            version=item.get("Version", 0),
            blob_url_get=item.get("BlobURLGet", ""),
            parent=item.get("Parent", ""),
            type=item.get("Type", "DocumentType"),
            bookmarked=item.get("Bookmarked", False),
            tags=item.get("Tags", []),
        )
        for item in items
        if item.get("Type") == "DocumentType"
    ]

def download_zip(self, document: RemarkableDocument, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{document.id}.zip"

    def _call():
        resp = requests.get(document.blob_url_get, timeout=120, stream=True)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)

    remarkable_breaker.call(_call)
    return dest_path
```

### `remarkable/sync.py` — `SyncManager.sync`

The sync manager needs access to `RemarkableClient` and `StateDB`. Accept them via constructor (dependency injection). The CLI will build them from settings.

**Dedup strategy:** `is_processed()` is page-scoped — pages don't exist as separate entities until Milestone 2 parses ZIPs. At the sync stage, use filesystem-level dedup: skip documents whose ZIP already exists in `download_dir`. This is simple and correct. M2 will write page-level entries to the DB when it extracts and processes `.rm` files.

```python
# src/rm_notebooklm/remarkable/sync.py

from rm_notebooklm.utils.logging import get_logger

class SyncManager:
    def __init__(self, client: RemarkableClient, download_dir: Path) -> None:
        self._client = client
        self._download_dir = download_dir
        self._log = get_logger(__name__)

    def sync(self, dry_run: bool = False) -> list[Path]:
        docs = self._client.list_documents()
        downloaded = []
        for doc in docs:
            zip_path = self._download_dir / f"{doc.id}.zip"
            if zip_path.exists():
                self._log.debug("skipping_existing", doc_id=doc.id, name=doc.vissible_name)
                continue
            if dry_run:
                self._log.info("would_download", doc_id=doc.id, name=doc.vissible_name)
                continue
            zip_path = self._client.download_zip(doc, self._download_dir)
            downloaded.append(zip_path)
        return downloaded
```

**Note:** The `StateDB` parameter is removed from `SyncManager.__init__` — it was unused in M1 and confused the scope. M2's parser will receive the download dir, extract pages, and call `state_db.mark_processed()` per page.

### `cli.py` — `sync` command

Wire up settings → client → SyncManager. Call `configure_logging` before any other work. In dry-run mode, track found documents via the log output (the `SyncManager` logs each `would_download` entry) — the returned `paths` list is always empty in dry-run mode by design.

```python
@app.command()
def sync(
    dry_run: bool = typer.Option(False, "--dry-run", help="List documents without downloading"),
) -> None:
    from rm_notebooklm.config import settings
    from rm_notebooklm.utils.logging import configure_logging
    from rm_notebooklm.remarkable.auth import refresh_user_token
    from rm_notebooklm.remarkable.client import RemarkableClient
    from rm_notebooklm.remarkable.sync import SyncManager

    configure_logging(level=settings.log_level, fmt=settings.log_format)

    user_token = settings.rm_user_token or refresh_user_token(settings.rm_device_token)
    client = RemarkableClient(device_token=settings.rm_device_token, user_token=user_token)
    download_dir = settings.state_db_path_expanded.parent / "downloads"

    manager = SyncManager(client=client, download_dir=download_dir)
    paths = manager.sync(dry_run=dry_run)

    if not dry_run:
        console.print(f"[green]Synced {len(paths)} documents[/green]")
```

---

## System-Wide Impact

- **No breaking changes** — all other milestones' stubs remain untouched (`upload_pdf`, `mark_pdf_uploaded`, all OCR/parsing/PDF modules)
- **`StateDB` not used in `SyncManager`** — `processed_pages` is page-scoped; pages don't exist until M2 parses ZIPs. M1 uses filesystem dedup (skip if ZIP exists). M2 writes DB entries per page.
- **State schema is locked** — the `processed_pages` table schema defined in `state/db.py` is shared by Milestones 1–5; do not add or remove columns here
- **`remarkable_breaker` is a module-level singleton** — all calls within a process share circuit state; correct for single-process CLI, fine for Milestone 1
- **`rm-api` library vs raw HTTP** — the blueprint specifies `rm-api==1.1.1` for sync15 protocol support, but device/user token registration uses raw POST endpoints that predate sync15. `rm-api` wraps these too; check its API before deciding whether to use it or raw `requests`. If `rm-api` handles auth natively, prefer it over duplicating the logic.

---

## Acceptance Criteria

- [x] `rm-notebooklm sync --dry-run` lists documents with their names, exits 0
- [x] `rm-notebooklm sync` downloads ZIPs to `~/.rm_notebooklm/downloads/`
- [x] Re-running `sync` on unchanged documents skips them (filesystem dedup — skip if ZIP exists)
- [x] A simulated 401 triggers token refresh and retry (covered by `test_token_refresh_on_401`)
- [x] `pytest tests/unit/ -v` passes with 0 skipped for Milestone 1 tests
- [x] `pytest tests/integration/ -v` passes (using `responses` mock; VCR cassettes recorded with real credentials later)
- [x] `ruff check src/ tests/` exits 0
- [x] `mypy src/` exits 0

---

## Implementation Order

Implement in this sequence to avoid breaking imports:

1. `src/rm_notebooklm/utils/logging.py` — no deps
2. `src/rm_notebooklm/utils/retry.py` — no deps
3. `src/rm_notebooklm/state/db.py` — `is_processed()`, `mark_processed()`
4. `src/rm_notebooklm/remarkable/auth.py` — `register_device()`, `refresh_user_token()`
5. `src/rm_notebooklm/remarkable/client.py` — `list_documents()`, `download_zip()`
6. `src/rm_notebooklm/remarkable/sync.py` — full `SyncManager` (constructor takes `client` + `download_dir`; no `StateDB` in M1)
7. `src/rm_notebooklm/cli.py` — `sync` command body
8. `tests/unit/test_state_db.py` — remove `pytest.skip()` calls
9. `tests/unit/test_auth.py` — remove `pytest.skip()` from `test_token_refresh_on_401`
10. `tests/integration/test_remarkable_api.py` — implement bodies + record VCR cassettes
    - Record once with real credentials: `pytest tests/integration/ --vcr-record=all`
    - Commit cassettes to `tests/fixtures/cassettes/`
    - CI runs with `--vcr-record=none` (already configured)

---

## Dependencies & Risks

| Risk | Mitigation |
|------|-----------|
| `rm-api==1.1.1` may already wrap auth endpoints | Check its API before implementing raw HTTP — prefer the library |
| reMarkable API returns `VissibleName` (typo) | Already handled in `RemarkableDocument.vissible_name` field |
| `pybreaker` v1.x API may differ from blueprint's `success_threshold` param | Verify constructor kwargs against installed version |
| VCR cassettes require real credentials to record | Record locally; cassettes are committed so CI never needs live access |
| `rm_user_token` empty on first run | `sync` command handles this: calls `refresh_user_token()` if empty |

---

## Sources & References

### Internal References

- Architecture: `docs/blueprint.md` — auth flows, sync15 rationale, circuit breaker patterns
- Milestones: `MILESTONES.md` — M1 issue list and acceptance criteria
- Config: `src/rm_notebooklm/config.py:17` — `Settings` class with all env vars
- Hashing (already done): `src/rm_notebooklm/utils/hashing.py:9`
- Decorator (already done): `src/rm_notebooklm/remarkable/auth.py:32`
- DB schema (already done): `src/rm_notebooklm/state/db.py:22`
- Test fixtures: `tests/conftest.py:75` — `tmp_state_db` fixture

### Key Library Decisions

- `rm-api==1.1.1` for sync15 — **do not use rmapy** (mentioned twice in CLAUDE.md for a reason)
- `tenacity>=8.0` + `pybreaker>=1.0` — already pinned in `pyproject.toml`
- `structlog>=24.0` — already pinned; use `structlog.stdlib.BoundLogger` for type annotations
- `requests>=2.31` — for sync HTTP calls; `httpx` available too but `requests` used throughout
