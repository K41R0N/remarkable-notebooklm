---
title: "First sync fires OCR on entire notebook history, hitting rate limits and cost overruns"
date: 2026-02-24
category: runtime-errors
tags:
  - ocr
  - rate-limiting
  - first-run
  - cost
  - cli-flags
  - performance
problem_type: performance-issue
severity: high
status: solved
milestone: M6-4
---

# First sync fires OCR on entire notebook history, hitting rate limits and cost overruns

## Symptom

Running `rm-notebooklm run` on a fresh install against a 100-page notebook triggers
100 OCR API calls in a single run. The run hits provider rate limits mid-way,
partially processes the notebook, leaves `processed_pages` in an inconsistent state,
and may incur significant API costs before the user has verified the pipeline works.

## Root Cause

On first run, `state.db` is empty — `is_processed()` returns `False` for every page.
The pipeline correctly processes all unprocessed pages, but there is no mechanism to
scope the first run to a manageable subset. A user who accumulated a year of notes
before installing the pipeline gets that entire history processed at once.

## Working Solution

Two CLI flags (M6-4) gate the scope of each run:

### `--since DATE` — skip pages older than a date

```bash
rm-notebooklm run --since 2026-02-01
```

Processes only pages created or modified on or after the given date. Useful for
excluding years of historical notes and focusing on recent content.

### `--max-pages N` — hard cap on pages per run

```bash
rm-notebooklm run --max-pages 20
```

Processes at most N new pages per notebook per run. Subsequent runs pick up where
the previous run left off (dedup via `is_processed(page_id, hash)` ensures no repeats).

### Recommended first-run pattern

```bash
# Step 1: smoke test — 10 recent pages, verify pipeline works end to end
rm-notebooklm run --max-pages 10 --since 2026-02-20

# Step 2: after verifying output PDF looks correct, process remaining recent pages
rm-notebooklm run --since 2026-01-01

# Step 3: normal scheduled operation (systemd fires every 10 min, processes only new pages)
# (no flags needed — state.db tracks what's already done)
```

### Cost estimate (Gemini 2.5 Flash, default provider)

| Pages | Estimated cost |
|-------|---------------|
| 10 | ~$0.02 |
| 50 | ~$0.10 |
| 100 | ~$0.20 |
| 500 | ~$1.00 |

Always use `--dry-run` first on a new notebook to preview page count before committing:

```bash
rm-notebooklm run --dry-run
# Output: "12 pages to process, estimated cost: $0.024"
```

## What NOT to Do

- Do not run `rm-notebooklm run` with no flags on a fresh install against a large notebook
- Do not set `--max-pages` to a very large number for the first smoke test
- Do not skip `--dry-run` before the first real run on an unfamiliar notebook

## Prevention

- Document `--max-pages 10 --since <recent-date>` as the recommended first-run invocation
  in `docs/deployment/systemd.md` and `docs/deployment/docker.md`
- Add the batched PDF size limit (100MB) guard before upload — large runs may generate
  PDFs that exceed the reMarkable file size limit (M5-6)
- The `--max-pages` and `--since` flags must be implemented before M6 deployment docs
  are published

## Related

- `MILESTONES.md:M6-4` — `--since` flag (date-based incremental sync)
- `MILESTONES.md:Known Risks` — "First run processes entire notebook history (Medium)"
- `docs/plans/2026-02-23-feat-notebook-notebooklm-mapping-plan.md` — Risk table entry
- `docs/solutions/runtime-errors/scheduled-pipeline-requires-host-not-device.md`
- `docs/solutions/runtime-errors/concurrent-sync-runs-deadlock-without-filelock.md`
