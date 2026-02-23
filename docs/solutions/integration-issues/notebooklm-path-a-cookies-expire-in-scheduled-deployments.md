---
title: "Path A (notebooklm-py) cookies expire every 1-2 weeks — incompatible with scheduled deployments"
date: 2026-02-24
category: integration-issues
tags:
  - notebooklm
  - path-a
  - cookies
  - authentication
  - scheduled-deployment
  - automation
problem_type: integration-issue
severity: critical
status: solved
milestone: M4C-2
---

# Path A (notebooklm-py) cookies expire every 1–2 weeks — incompatible with scheduled deployments

## Symptom

Pipeline runs fine locally for a week or two, then suddenly stops producing
responses. `rm-notebooklm run` in the systemd journal shows authentication errors
from `notebooklm-py`. Running `notebooklm login` fixes it temporarily, then the
same failure recurs 1–2 weeks later.

## Root Cause

Path A uses `notebooklm-py` (an unofficial client that reverse-engineers the
NotebookLM browser API). Authentication is cookie-based: the user logs in via a
Playwright Chromium browser once, and session cookies are saved to
`~/.notebooklm/storage_state.json`. These cookies carry the Google session and
expire on Google's schedule — typically 1–2 weeks.

There is no automated renewal path. The only way to refresh is to run
`notebooklm login` interactively, which requires a browser. A headless server
cannot do this.

## Working Solution

**Never use Path A for scheduled/daemon deployments.** Path A is local development
and prototyping only.

### Switch to Path C (recommended)

```bash
# .env
NOTEBOOKLM_PATH=C           # Gemini API with document grounding
GEMINI_API_KEY=AIza...      # Permanent API key — never expires
GCS_BUCKET_NAME=my-bucket
```

Path C is fully automated, uses a permanent API key, and does not require any
browser or OAuth flow. It is the **only Path compatible with all deployment
targets** (laptop, server, Raspberry Pi, Docker, GitHub Actions).

### If you need the NotebookLM UI (Path A use cases)

Use Path A **only** on a developer machine where you can run `notebooklm login`
whenever it expires. Never deploy Path A to any scheduled context.

### Deployment compatibility matrix

| Deployment target | Path A | Path B | Path C |
|-------------------|--------|--------|--------|
| Developer laptop (manual) | ✅ | ✅ | ✅ |
| Systemd timer / cron | ❌ | ✅ | ✅ |
| Docker container | ❌ | ✅ | ✅ |
| GitHub Actions | ❌ | ✅ | ✅ |
| Raspberry Pi unattended | ❌ | ✅ | ✅ |

### Cookie expiry error (M4C-2)

`notebooklm/unofficial.py` must detect expired cookies and fail with a clear
message rather than a cryptic stack trace:

```python
# In NotebookLMUnofficialClient.query()
if response.status_code in (401, 403):
    raise CookieExpiredError(
        "Path A authentication expired. Run `notebooklm login` to refresh "
        "cookies. This path cannot be used for scheduled/unattended deployments. "
        "Consider switching to NOTEBOOKLM_PATH=C."
    )
```

## What NOT to Do

- Do not deploy Path A to any systemd service, Docker container, or cron job
- Do not document Path A as a deployment option in systemd/Docker setup guides
  without a prominent warning box
- Do not set `NOTEBOOKLM_PATH=A` in production `.env` files

## Prevention

- Config validator: if `NOTEBOOKLM_PATH=A` and the process is running under
  systemd (check `INVOCATION_ID` env var) or in Docker (check `/.dockerenv`),
  log a critical warning and exit 1 with instructions to switch to Path C
- CI always uses Path C — `NOTEBOOKLM_PATH=A` is never set in CI environment

## Related

- `MILESTONES.md:M4C-2` — cookie expiry detection with helpful error message
- `MILESTONES.md:Known Risks` — "Cookie expiry in CI for Path A (Certain)"
- `docs/solutions/security-issues/google-oauth-token-json-incompatible-with-headless-deployments.md`
- `docs/solutions/runtime-errors/scheduled-pipeline-requires-host-not-device.md`
- `CLAUDE.md` — "Path A (`notebooklm-py`): cookies expire every 1–2 weeks; only for prototyping"
- `.env.example` — `NOTEBOOKLM_PATH=C` is the documented default
