---
title: "SyncManager dedup must be document-scoped (filesystem), not page-scoped (SQLite)"
date: 2026-02-23
category: logic-errors
tags:
  - sync
  - dedup
  - state-management
  - scope-mismatch
  - architecture
  - SyncManager
  - StateDB
problem_type: architecture
severity: high
status: solved
milestone: M1
---

# SyncManager dedup must be document-scoped (filesystem), not page-scoped (SQLite)

## Symptom / Design Mistake

A natural first instinct is to add `StateDB` to `SyncManager` and call `is_processed()`
inside the sync loop to skip already-processed documents:

```python
# ❌ WRONG — do not write this
class SyncManager:
    def __init__(
        self,
        client: RemarkableClient,
        download_dir: Path,
        state_db: StateDB,          # ← wrong dependency
    ) -> None:
        ...

    def sync(self, dry_run: bool = False) -> list[Path]:
        for doc in self._client.list_documents():
            if self._state_db.is_processed(doc.id, hash_doc(doc)):   # ← wrong scope
                continue
            ...
```

This silently does the wrong thing because `doc.id` is a **document UUID** but
`is_processed()` expects a **page UUID**. The method signature is:

```python
def is_processed(self, page_id: str, content_hash: str) -> bool:
```

`page_id` refers to the UUID of an individual `.rm` file *inside* a ZIP — an entity that
does not exist until Milestone 2 parses the ZIP. Passing a document UUID here either
silently never matches (so dedup never fires) or creates phantom state entries.

## Root Cause

Two different entity scopes are being conflated:

| Entity | UUID source | Exists at | Used by |
|--------|------------|-----------|---------|
| **Document** | reMarkable Cloud API (`doc.id`) | M1 sync time | `SyncManager` |
| **Page** | Inside `.rm` file within the ZIP | M2 parse time | `StateDB`, OCR, PDF |

At M1 sync time, only documents exist. Pages are nested inside ZIPs and only become
queryable after M2 extracts and parses `.rm` files. There are no page UUIDs to look up.

## Solution

Use **filesystem-level dedup** at the document scope: skip any document whose ZIP file
already exists in `download_dir`. `StateDB` is not needed in `SyncManager` at all.

```python
# ✅ CORRECT
class SyncManager:
    """Orchestrates incremental reMarkable → local sync.

    Dedup strategy: skip documents whose ZIP already exists in download_dir
    (filesystem-level, document-scoped). Page-level dedup is handled by M2
    (parse stage) via StateDB.mark_processed() per extracted page.
    """

    def __init__(self, client: RemarkableClient, download_dir: Path) -> None:
        self._client = client
        self._download_dir = download_dir
        self._log = get_logger(__name__)
        # No StateDB — page-level state is M2's responsibility

    def sync(self, dry_run: bool = False) -> list[Path]:
        docs = self._client.list_documents()
        downloaded: list[Path] = []

        for doc in docs:
            zip_path = self._download_dir / f"{doc.id}.zip"
            if zip_path.exists():                              # ← filesystem dedup
                self._log.debug(
                    "skipping_existing",
                    doc_id=doc.id,
                    name=doc.vissible_name,
                )
                continue
            if dry_run:
                self._log.info("would_download", doc_id=doc.id)
                continue
            zip_path = self._client.download_zip(doc, self._download_dir)
            downloaded.append(zip_path)

        return downloaded
```

## The Two-Layer Dedup Architecture

This is intentional. Each milestone owns its own dedup scope:

```
M1 (SyncManager.sync)
  └─ Scope: document (ZIP file)
  └─ Method: filesystem — if zip_path.exists(): skip
  └─ No DB access

M2 (parse + OCR)
  └─ Scope: page (individual .rm file inside ZIP)
  └─ Method: SQLite — StateDB.is_processed(page_id, content_hash)
  └─ On process: StateDB.mark_processed(page_id, notebook_id, content_hash, ...)
```

**Rule:** M1 code must never import from `state/`. M2+ code calls `StateDB` per page.

### How M2 will use StateDB

When Milestone 2 is implemented, it receives the ZIP path and calls `mark_processed()`
for each extracted page:

```python
# M2 pseudocode — not yet implemented
for page_id, rm_bytes in extract_pages(zip_path):
    content_hash = hash_bytes(rm_bytes)
    if state_db.is_processed(page_id, content_hash):
        continue                                    # page unchanged, skip OCR
    text = ocr_provider.transcribe(rm_bytes)
    state_db.mark_processed(
        page_id=page_id,
        notebook_id=doc.id,
        content_hash=content_hash,
        ocr_text=text,
        version=doc.version,
    )
```

Note: `page_id` here is the UUID of the `.rm` file from inside the ZIP — a completely
different identifier than `doc.id`.

## Prevention

### Docstring on `StateDB.is_processed`

The method docstring should make the scope explicit so future contributors cannot miss it:

```python
def is_processed(self, page_id: str, content_hash: str) -> bool:
    """Return True if this exact page version has been processed.

    PAGE-SCOPED: `page_id` is the UUID of an individual .rm file extracted
    from a document ZIP (M2 parse stage). Do NOT pass a document UUID here.

    For document-level dedup (M1 sync), use filesystem check:
        if (download_dir / f"{doc.id}.zip").exists(): skip
    """
```

### Enforce the boundary in tests

```python
# tests/unit/test_sync.py
def test_syncmanager_init_has_no_statedb_param():
    """SyncManager must not accept StateDB."""
    import inspect
    from rm_notebooklm.remarkable.sync import SyncManager
    sig = inspect.signature(SyncManager.__init__)
    assert "state_db" not in sig.parameters
    assert "db" not in sig.parameters

def test_syncmanager_skips_existing_zip(tmp_path):
    """Filesystem dedup: existing ZIP → no download attempt."""
    from unittest.mock import MagicMock
    from rm_notebooklm.remarkable.sync import SyncManager
    from rm_notebooklm.remarkable.client import RemarkableDocument

    doc = RemarkableDocument(id="abc-123", vissible_name="Test", ...)
    (tmp_path / "abc-123.zip").touch()           # simulate already-downloaded

    client = MagicMock()
    client.list_documents.return_value = [doc]

    mgr = SyncManager(client=client, download_dir=tmp_path)
    result = mgr.sync()

    assert result == []
    client.download_zip.assert_not_called()
```

## Related

- `src/rm_notebooklm/remarkable/sync.py` — correct implementation
- `src/rm_notebooklm/state/db.py` — `is_processed()` and `mark_processed()` (page-scoped)
- `CLAUDE.md § State Management` — SQLite schema, page hash dedup strategy
- `MILESTONES.md § Milestone 1` — acceptance criteria; M1 dedup is filesystem-based
- `docs/plans/2026-02-23-feat-milestone-1-remarkable-sync-plan.md § System-Wide Impact`
  — explicit note: "StateDB not used in SyncManager — processed_pages is page-scoped"
