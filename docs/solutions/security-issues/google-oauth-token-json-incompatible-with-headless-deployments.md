---
title: "Desktop OAuth token.json expires silently on headless servers"
date: 2026-02-24
category: security-issues
tags:
  - authentication
  - oauth
  - service-account
  - headless
  - google-auth
  - deployment
  - credential-management
problem_type: integration-issue
severity: critical
status: solved
milestone: M6-6g
---

# Desktop OAuth token.json expires silently on headless servers

## Symptom

The pipeline works perfectly on a developer laptop. After deploying to a
Raspberry Pi / VPS / home server, it runs for a few days then silently fails
with `google.auth.exceptions.RefreshError: Token has been expired or revoked`.
The systemd unit enters a failed state. No new PDFs appear on the reMarkable.

## Root Cause

`scripts/setup_google_auth.py` uses Google's three-legged desktop OAuth flow:
a browser opens, the user logs in, and a `token.json` refresh token is written.
On a server with no browser, the refresh token eventually expires and cannot be
renewed interactively. The `google-auth-oauthlib` library has no headless renewal
path for user credentials.

This affects **Paths A and B** (both use the Google APIs that require OAuth).

## Working Solution

### Option 1: Path C — Gemini grounding (recommended for servers)

Path C uses only `GEMINI_API_KEY` — a permanent API key that never expires.
No OAuth, no `token.json`, no service account setup required.

```bash
# .env
NOTEBOOKLM_PATH=C
GEMINI_API_KEY=AIza...      # From Google AI Studio (free tier available)
GCS_BUCKET_NAME=my-bucket   # GCS bucket for document uploads
```

This is the **recommended deployment path** for all unattended servers.

### Option 2: GCP service account JSON key (for Path B / Enterprise API)

If you must use Path B (NotebookLM Enterprise), replace `token.json` with a
service account key:

1. In [GCP Console → IAM → Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts),
   create a service account with the required scopes (Drive API, Discovery Engine)
2. Download the JSON key file
3. Set in `.env`:
   ```bash
   GOOGLE_CREDENTIALS_JSON=/etc/rm-notebooklm/service-account.json
   # Do NOT set GOOGLE_TOKEN_JSON — it is ignored when using a service account
   ```
4. The `google-api-python-client` library auto-detects service account keys and
   never requires interactive refresh

### Credential headless-safety matrix

| Path | Credential type | Headless-safe? | Notes |
|------|----------------|----------------|-------|
| C (Gemini grounding) | `GEMINI_API_KEY` | ✅ yes | Recommended for all server deployments |
| B (Enterprise API) | Service account JSON | ✅ yes | Requires GCP project |
| B (Enterprise API) | `token.json` (desktop OAuth) | ❌ no | Expires; cannot renew on server |
| A (unofficial) | Browser cookies | ❌ no | See separate doc for Path A |

## What NOT to Do

- Do not copy `token.json` from your laptop to the server — it will expire the same way
- Do not set `GOOGLE_TOKEN_JSON` in server deployments — use service account JSON instead
- Do not read `token.json` from any code path other than `scripts/setup_google_auth.py`

## Prevention

- The canonical server deployment guide is `docs/deployment/headless-credentials.md`
  (M6-6g) — link to it from every deployment doc
- Add a config validator: if `DEPLOYMENT_MODE=always_on_service` and
  `NOTEBOOKLM_PATH in ("A", "B")` and `GOOGLE_TOKEN_JSON` is set (not a service
  account path), raise `ConfigurationError` with instructions
- CI should never attempt real OAuth — mock `google.auth.oauthlib` in all tests

## Related

- `MILESTONES.md:M6-6g` — `docs/deployment/headless-credentials.md` (to be written in M6)
- `docs/solutions/integration-issues/notebooklm-path-a-cookies-expire-in-scheduled-deployments.md`
- `docs/solutions/runtime-errors/scheduled-pipeline-requires-host-not-device.md`
- `docs/plans/2026-02-23-feat-notebook-notebooklm-mapping-plan.md` — credentials table
- `scripts/setup_google_auth.py` — desktop OAuth (development only)
