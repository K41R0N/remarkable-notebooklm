---
title: "feat: per-notebook NotebookLM mapping with per-page dedup"
type: feat
status: active
date: 2026-02-23
---

# feat: per-notebook NotebookLM mapping with per-page dedup

## Overview

A cross-cutting feature that enables many-to-many mapping between reMarkable
notebooks and NotebookLM projects, with idempotent per-page processing. Each
notebook has its own dedicated NotebookLM project. Running the pipeline multiple
times is always safe — new pages are processed, processed pages are skipped.

---

## The Workflow (user perspective)

```
reMarkable folder structure:

  My Research/                    ← rm_folder
    Questions.rm                  ← rm_notebook (source of questions)
    responses/                    ← auto-created subfolder
      2026-02-23-session.pdf      ← batched Q&A for that run

  Machine Learning/
    Deep Learning Notes.rm
    responses/
      2026-02-24-session.pdf
```

**Each run (`rm-notebooklm run`):**

1. Load `~/.rm_notebooklm/mappings.yaml`
2. For each mapping entry, download the notebook if not already cached
3. For each **new or edited page** in the notebook:
   - Parse page: typed text (direct) or handwriting → OCR
   - Skip if `(page_id, content_hash)` already in `processed_pages` DB
4. Batch all new Q&A pairs into one PDF for this run
5. Upload PDF to `rm_folder/responses/` on reMarkable
6. Add the PDF as a source in the corresponding NotebookLM project
7. Mark all processed pages in the DB (`notebooklm_nb_id` stored per page)

**Per-page dedup guarantee:**
- Same page, same content → always skipped (already processed)
- Same page, edited content → reprocessed (content hash changed)
- New page with same text as an old page → processed (different `page_id` = intentional)
- Safe to run the pipeline as many times as you want

**Trigger:** Manual (`rm-notebooklm run`) today; systemd timer added in M6.

---

## mappings.yaml Schema

```yaml
# ~/.rm_notebooklm/mappings.yaml
# Kept OUTSIDE the repo — never committed to git.

mappings:
  - rm_folder: "My Research"            # reMarkable folder VissibleName
    rm_notebook: "Questions"            # notebook VissibleName inside that folder
    notebooklm_nb_id: "abc123def456"    # NotebookLM notebook/corpus ID
    responses_folder: "responses"       # subfolder name (default: "responses")
    notebooklm_path: C                  # optional path override (A/B/C); default from env

  - rm_folder: "Machine Learning"
    rm_notebook: "Deep Learning Notes"
    notebooklm_nb_id: "xyz789uvw012"
    # responses_folder defaults to "responses"
    # notebooklm_path defaults to NOTEBOOKLM_PATH env var
```

**Field semantics:**

| Field | Required | Description |
|-------|----------|-------------|
| `rm_folder` | yes | The reMarkable folder name (`VissibleName` — intentional API typo) |
| `rm_notebook` | yes | The notebook's `VissibleName` within that folder |
| `notebooklm_nb_id` | yes | NotebookLM project/notebook ID |
| `responses_folder` | no | Subfolder name for PDFs (default: `"responses"`) |
| `notebooklm_path` | no | `A`, `B`, or `C` (default: `NOTEBOOKLM_PATH` env var) |

---

## Technical Design

### New module: `src/rm_notebooklm/mapping/`

```
src/rm_notebooklm/mapping/
├── __init__.py          # exports: MappingEntry, load_mappings, resolve_mapping_uuids
├── models.py            # MappingEntry (Pydantic), MappingsConfig
├── loader.py            # load_mappings(path) → list[MappingEntry]
└── resolver.py          # resolve_uuids(mapping, client) → ResolvedMapping
```

**`models.py`** — Pydantic models for validation:

```python
from pydantic import BaseModel, Field
from typing import Literal

class MappingEntry(BaseModel):
    rm_folder: str
    rm_notebook: str
    notebooklm_nb_id: str
    responses_folder: str = "responses"
    notebooklm_path: Literal["A", "B", "C"] | None = None

class MappingsConfig(BaseModel):
    mappings: list[MappingEntry]
```

**`loader.py`** — YAML → validated model:

```python
import yaml
from pathlib import Path
from rm_notebooklm.mapping.models import MappingEntry, MappingsConfig

def load_mappings(path: Path) -> list[MappingEntry]:
    """Load and validate mappings.yaml. Returns empty list if file absent."""
    expanded = path.expanduser()
    if not expanded.exists():
        return []
    with expanded.open() as f:
        raw = yaml.safe_load(f)
    return MappingsConfig.model_validate(raw).mappings
```

**`resolver.py`** — resolves human-readable names to reMarkable UUIDs:

```python
from dataclasses import dataclass
from rm_notebooklm.mapping.models import MappingEntry
from rm_notebooklm.remarkable.client import RemarkableClient

@dataclass
class ResolvedMapping:
    entry: MappingEntry
    rm_folder_id: str           # reMarkable UUID for the folder
    rm_document_id: str         # reMarkable UUID for the notebook
    rm_responses_folder_id: str | None  # None if responses/ subfolder not yet created

def resolve_mapping_uuids(
    entry: MappingEntry,
    client: RemarkableClient,
) -> ResolvedMapping:
    """Resolve folder + notebook names to reMarkable UUIDs."""
    folders = client.list_folders()           # new method — see below
    folder = next((f for f in folders if f.vissible_name == entry.rm_folder), None)
    if folder is None:
        raise ValueError(f"reMarkable folder not found: {entry.rm_folder!r}")

    docs = client.list_documents()
    notebook = next(
        (d for d in docs if d.vissible_name == entry.rm_notebook
         and d.parent == folder.id),
        None,
    )
    if notebook is None:
        raise ValueError(
            f"Notebook {entry.rm_notebook!r} not found in folder {entry.rm_folder!r}"
        )

    responses_folder = next(
        (f for f in folders
         if f.vissible_name == entry.responses_folder and f.parent == folder.id),
        None,
    )

    return ResolvedMapping(
        entry=entry,
        rm_folder_id=folder.id,
        rm_document_id=notebook.id,
        rm_responses_folder_id=responses_folder.id if responses_folder else None,
    )
```

---

### Changes to existing files

#### `src/rm_notebooklm/remarkable/client.py`

Add `list_folders()` method — `list_documents()` currently filters out `CollectionType`.
Need a separate method that returns folder items:

```python
def list_folders(self) -> list[RemarkableDocument]:
    """Return all collection (folder) items from the cloud."""
    # Same auth + circuit breaker pattern as list_documents()
    # Filter: item.get("Type") == "CollectionType"
```

Also add a `RemarkableFolder` dataclass or reuse `RemarkableDocument` with `type="CollectionType"`.
Using `RemarkableDocument` with the existing `type` field is cleaner — no new type needed.

#### `src/rm_notebooklm/config.py`

Add field and property (follow `state_db_path` pattern at `config.py:88`):

```python
rm_notebook_mappings_file: Path = Field(
    default=Path("~/.rm_notebooklm/mappings.yaml"),
    description="Path to YAML mapping reMarkable notebooks to NotebookLM projects",
)

@property
def rm_notebook_mappings_file_expanded(self) -> Path:
    return self.rm_notebook_mappings_file.expanduser()
```

#### `src/rm_notebooklm/state/db.py`

Wire `notebooklm_nb_id` into `mark_processed()` — the column already exists in the schema
but the INSERT at line 100 does not set it:

```python
def mark_processed(
    self,
    *,
    page_id: str,
    notebook_id: str,
    content_hash: str,
    ocr_text: str | None = None,
    version: int,
    notebooklm_nb_id: str | None = None,   # ← add this param
) -> None:
    ...
    conn.execute(
        """INSERT INTO processed_pages
           (page_id, notebook_id, content_hash, ocr_text, notebooklm_nb_id,
            processed_at, version)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(page_id) DO UPDATE SET
             content_hash=excluded.content_hash,
             ocr_text=excluded.ocr_text,
             notebooklm_nb_id=excluded.notebooklm_nb_id,
             processed_at=excluded.processed_at,
             version=excluded.version
        """,
        (page_id, notebook_id, content_hash, ocr_text, notebooklm_nb_id, now, version),
    )
```

#### `pyproject.toml`

Add `PyYAML` to main dependencies (mapping config is core, not optional):

```toml
"PyYAML>=6.0",
```

Add to `[[tool.mypy.overrides]]` ignore list:

```toml
module = ["yaml"]
```

---

## System-Wide Impact

### Interaction graph

```
cli.py run
  └─ load_mappings(settings.rm_notebook_mappings_file_expanded)
       └─ yaml.safe_load → MappingsConfig.model_validate
  └─ resolve_mapping_uuids(entry, client)
       └─ client.list_folders()   ← new API call (circuit-breaker wrapped)
       └─ client.list_documents() ← existing
  └─ sync_manager.sync_document(rm_document_id)  ← narrow sync, not all docs
  └─ [M2] parse_pages(zip_path)
       └─ for each page:
            └─ state_db.is_processed(page_id, content_hash) → skip if True
            └─ [M3] ocr_provider.transcribe(png_bytes)
  └─ [M4] notebooklm_client.query(questions, project_id=entry.notebooklm_nb_id)
  └─ [M5] pdf_generator.generate(qa_pairs) → PDF bytes
  └─ [M5] client.upload_pdf(pdf, parent_id=rm_responses_folder_id)
  └─ [M4] notebooklm_client.add_source(pdf_url, project_id=entry.notebooklm_nb_id)
  └─ state_db.mark_processed(notebooklm_nb_id=entry.notebooklm_nb_id, ...)
```

### Per-page dedup: how it prevents repeats

```
Run 1: notebook has pages [P1, P2, P3]
  → P1, P2, P3 all new → process all 3 → mark processed
  → 1 PDF "2026-02-23-session.pdf" with 3 Q&A pairs

Run 2: notebook has pages [P1, P2, P3, P4]
  → P1: is_processed(P1.id, P1.hash) = True → SKIP
  → P2: is_processed(P2.id, P2.hash) = True → SKIP
  → P3: is_processed(P3.id, P3.hash) = True → SKIP
  → P4: is_processed(P4.id, P4.hash) = False → PROCESS
  → 1 PDF "2026-02-24-session.pdf" with 1 Q&A pair

Run 3: user edits P2 (rewrites the question)
  → P2: is_processed(P2.id, NEW_hash) = False → REPROCESS
  → P4: is_processed(P4.id, P4.hash) = True → SKIP
  → 1 PDF with 1 updated Q&A for P2

"Same question written on page 5" (intentional repeat):
  → P5 has new page_id → is_processed(P5.id, any_hash) = False → PROCESS
  → Gets its own answer (correct behaviour — user wrote it intentionally)
```

### State lifecycle risks

- **`responses/` folder doesn't exist yet:** `resolve_mapping_uuids` returns
  `rm_responses_folder_id=None`. The M5 upload step must create the folder (one API
  call to create a `CollectionType` document with `parent=rm_folder_id`) before
  uploading the PDF, then cache the new folder ID in the DB.
- **Mapping config is read fresh on every `run`:** If `notebooklm_nb_id` changes in the
  YAML, old processed pages in the DB retain the old `notebooklm_nb_id`. This is
  harmless — the pages themselves are already processed; the new ID only applies to
  future pages.
- **YAML parse failure at startup:** If `mappings.yaml` is malformed, `load_mappings()`
  raises a Pydantic `ValidationError`. This is a hard failure at startup — do not
  silently continue with zero mappings. Log the error and exit 1.

### No impact on M1 SyncManager

`SyncManager.sync()` is unchanged. Mapping-aware download is layered above it:
instead of `sync_manager.sync()` (downloads everything), the `run` command calls
`client.download_zip(resolved.rm_document_id)` directly for each mapped notebook only.

---

## Acceptance Criteria

- [ ] `~/.rm_notebooklm/mappings.yaml` with one entry → `rm-notebooklm run` processes
  only that notebook (not all synced documents)
- [ ] Running `rm-notebooklm run` twice → second run processes zero new pages (all
  pages in `processed_pages` with correct `content_hash`)
- [ ] Adding a new page to the reMarkable notebook, then running → only the new page
  is processed; existing pages are skipped
- [ ] Editing an existing page (content changes) → page is reprocessed; others skipped
- [ ] Two notebooks mapped to two different NotebookLM projects → each gets its own
  Q&A PDF uploaded to its own `responses/` folder
- [ ] Missing `mappings.yaml` → `rm-notebooklm run` exits 1 with a clear error message
  pointing to `.env.example` for setup instructions
- [ ] `rm_notebook_mappings_file` present in `Settings` and respected from `.env`
- [ ] `ruff check src/ tests/` exits 0
- [ ] `mypy src/` exits 0 (all new code fully annotated)
- [ ] Unit tests cover: mapping load, validation error cases, UUID resolution,
  dedup skip logic, `mark_processed` with `notebooklm_nb_id`

---

## Implementation Order

Implement in this sequence to avoid broken imports at each step:

1. **`pyproject.toml`** — add `PyYAML>=6.0`; add `yaml` to mypy overrides
2. **`src/rm_notebooklm/mapping/models.py`** — `MappingEntry`, `MappingsConfig`
3. **`src/rm_notebooklm/mapping/loader.py`** — `load_mappings(path)`
4. **`src/rm_notebooklm/config.py`** — add `rm_notebook_mappings_file` + expanded prop
5. **`src/rm_notebooklm/remarkable/client.py`** — add `list_folders()` method
6. **`src/rm_notebooklm/mapping/resolver.py`** — `resolve_mapping_uuids(entry, client)`
7. **`src/rm_notebooklm/mapping/__init__.py`** — export public API
8. **`src/rm_notebooklm/state/db.py`** — add `notebooklm_nb_id` param to `mark_processed`
9. **`docs/notebook-mappings.md`** — user-facing YAML reference (referenced in `.env.example`)
10. **`tests/unit/test_mapping_loader.py`** — YAML load, validation, empty file
11. **`tests/unit/test_mapping_resolver.py`** — UUID resolution with mocked client
12. **`tests/unit/test_state_db.py`** — add test for `mark_processed` with `notebooklm_nb_id`
13. **`cli.py run` command** — wire mappings into the `run` orchestration (M6 stub → M4/5)

Steps 1–9 can be merged as a standalone PR independent of M2/M3/M4.
Steps 10–12 ship with steps 1–9 in the same PR.
Step 13 is gated behind M4 and M5 being implemented.

---

## When credentials are needed

| Step | What | When |
|------|------|------|
| Steps 1–12 | Nothing — all local | Implement now |
| M2 (parsing) | Nothing | Implement next |
| M3 (OCR) | `GEMINI_API_KEY` (free tier) | Before M3 testing |
| M4 (NotebookLM) | `GOOGLE_CREDENTIALS_JSON` + OAuth flow + NotebookLM project IDs | Before M4 testing; see `scripts/setup_google_auth.py` |
| M5 (upload) | `RM_DEVICE_TOKEN` (one-time via `scripts/register_device.py`) | Before M5 E2E testing |

**First credential you need:** `GEMINI_API_KEY` from Google AI Studio (free, instant).
Run `scripts/setup_google_auth.py` for the Google OAuth well before M4.

---

## Dependencies & Risks

| Risk | Mitigation |
|------|-----------|
| `responses/` subfolder doesn't exist on first run | M5 upload creates it via `client.create_folder(name, parent_id)` — needs a new `create_folder()` method on `RemarkableClient` |
| `notebooklm_project_id` key name in YAML vs `notebooklm_nb_id` in DB | Model uses `notebooklm_nb_id` to match the DB column; `.env.example` YAML example updated accordingly |
| User fat-fingers folder/notebook name in YAML | `resolve_mapping_uuids` raises `ValueError` with the unmatched name; CLI catches and exits 1 with actionable message |
| reMarkable renames a folder (VissibleName changes) | Resolver fails; user must update `mappings.yaml`; could cache resolved UUIDs in DB to warn on name mismatch |
| Large notebook (100+ pages) on first run | Batched PDF might hit 100MB limit; apply per-run page limit (e.g. 50 pages max) with a `--max-pages` flag |
| PyYAML security (arbitrary code execution via `yaml.load`) | Always use `yaml.safe_load`, never `yaml.load` — enforced in `loader.py` |

---

## Sources & References

- `src/rm_notebooklm/state/db.py:22` — `processed_pages` schema (`notebooklm_nb_id` column)
- `src/rm_notebooklm/remarkable/client.py:34` — `RemarkableDocument.parent` field
- `src/rm_notebooklm/config.py:88` — `state_db_path` + `state_db_path_expanded` pattern to follow
- `docs/solutions/logic-errors/sync-dedup-document-level.md` — M1/M2 dedup scope boundary
- `MILESTONES.md:M6-3` — `--notebook-filter` flag (future CLI hook for mappings)
- `.env.example:72` — `RM_NOTEBOOK_MAPPINGS_FILE` already documented
