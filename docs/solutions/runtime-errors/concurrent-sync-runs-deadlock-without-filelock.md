---
title: "Concurrent pipeline invocations race on SQLite and produce duplicate PDFs without a file lock"
date: 2026-02-24
category: runtime-errors
tags:
  - concurrency
  - race-condition
  - state-management
  - file-locking
  - exit-codes
  - systemd
problem_type: logic-error
severity: critical
status: solved
milestone: M1-10
---

# Concurrent pipeline invocations race on SQLite and produce duplicate PDFs without a file lock

## Symptom

A systemd timer fires `rm-notebooklm run` every 10 minutes. A slow OCR run
(50 pages of handwriting) takes 15 minutes. Before the first run completes, the
timer fires again. Two processes now race on:

- `processed_pages` SQLite writes (`mark_processed()`)
- NotebookLM source upload
- PDF upload to reMarkable

Result: duplicate Q&A PDFs appear in the `responses/` folder, pages are double-counted
in the DB, and `is_processed()` returns stale reads.

## Root Cause

No locking primitive guards the `run` command. Each invocation checks
`is_processed(page_id, hash)`, sees the page as unprocessed (the first run hasn't
committed yet), and proceeds to OCR + upload it independently.

## Working Solution

Implement an exclusive file lock in `src/rm_notebooklm/state/lock.py` using
`fcntl.flock` (POSIX). Acquire the lock at the very start of `rm-notebooklm run`,
before any API calls. If the lock is already held (first run in progress), **exit 0**.

```python
# src/rm_notebooklm/state/lock.py
import fcntl
import sys
from pathlib import Path
import structlog

log = structlog.get_logger()

class PipelineLock:
    def __init__(self, lock_path: Path) -> None:
        self._path = lock_path
        self._fh = None

    def __enter__(self) -> "PipelineLock":
        self._fh = self._path.open("w")
        try:
            fcntl.flock(self._fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log.info("pipeline_already_running", lock=str(self._path))
            sys.exit(0)   # ← exit 0, NOT 1
        return self

    def __exit__(self, *_) -> None:
        if self._fh:
            fcntl.flock(self._fh, fcntl.LOCK_UN)
            self._fh.close()
```

Usage in `cli.py`:

```python
@app.command()
def run(ctx: typer.Context) -> None:
    settings = ctx.obj
    lock_path = settings.state_db_path_expanded.parent / ".pipeline.lock"
    with PipelineLock(lock_path):
        _run_pipeline(settings)
```

### Why exit 0 (not 1) when lock is held

| Exit code | systemd interpretation |
|-----------|----------------------|
| `0` | Unit succeeded — timer is happy |
| `1` | Unit **failed** — systemd marks it failed, sends alerts |

A skipped run because a previous run is still in progress is **not a failure**.
It is the correct behaviour for a cron/timer context. Exit 1 would generate
false-positive failure alerts for every slow OCR run.

## Prevention

- M1-10 is a **blocking gate for M6 systemd documentation** — do not publish
  systemd/Docker deployment docs until this lock is implemented and tested
- Test with threading: `test_concurrent_runs_skip_cleanly` in
  `tests/integration/test_run_lock.py` (see Prevention Strategist notes)
- Never skip lock acquisition in `--dry-run` mode — dry runs still touch the DB

## Related

- `MILESTONES.md:M1-10` — implementation issue
- `MILESTONES.md:M6` — exit code contract (0 / 1 / 75)
- `docs/solutions/runtime-errors/scheduled-pipeline-requires-host-not-device.md`
- `docs/plans/2026-02-23-feat-notebook-notebooklm-mapping-plan.md` — State lifecycle risks
