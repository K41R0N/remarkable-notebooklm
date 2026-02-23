---
title: "Pipeline must run on an always-on host, not the reMarkable tablet"
date: 2026-02-24
category: runtime-errors
tags:
  - deployment
  - architecture
  - systemd
  - scheduling
  - server-side
problem_type: architecture-decision
severity: critical
status: solved
milestone: M6
---

# Pipeline must run on an always-on host, not the reMarkable tablet

## Symptom

The reMarkable tablet is the *input device* — it writes `.rm` files to reMarkable Cloud.
The pipeline (`rm-notebooklm run`) cannot and does not run on the tablet itself.
Early planning left this implicit; new contributors expected to trigger the pipeline
manually from a laptop or assumed the tablet would drive the process.

## Root Cause

The original plan described `rm-notebooklm run` as a CLI command without specifying
*where* it executes. The tablet has no persistent shell access, no internet-facing
SDK support, and no ability to run scheduled Python processes. It is write-only from
the pipeline's perspective.

## Working Solution

Run `rm-notebooklm run` on an **always-on machine** that has:
- Persistent internet connectivity
- The `.env` file with all credentials
- A scheduler to trigger it on a regular interval

### Primary: systemd timer (Linux server / Raspberry Pi)

```ini
# systemd/rm-notebooklm.timer
[Unit]
Description=reMarkable → NotebookLM pipeline timer

[Timer]
OnCalendar=*:0/10          # Every 10 minutes
Persistent=true            # Fire missed runs after sleep/reboot

[Install]
WantedBy=timers.target
```

```ini
# systemd/rm-notebooklm.service
[Unit]
Description=reMarkable → NotebookLM pipeline

[Service]
Type=oneshot
ExecStart=/path/to/.venv/bin/rm-notebooklm run
EnvironmentFile=/etc/rm-notebooklm/env
```

### Alternative: Docker + host cron

```bash
# /etc/cron.d/rm-notebooklm
*/10 * * * * root docker run --rm \
  --env-file /etc/rm-notebooklm/env \
  -v /etc/rm-notebooklm:/secrets:ro \
  -v ~/.rm_notebooklm:/state \
  rm-notebooklm run
```

### Exit code contract (required for scheduler integration)

| Exit code | Meaning |
|-----------|---------|
| `0` | Success **or** no new pages to process (both are normal) |
| `1` | Hard failure (invalid credentials, malformed `mappings.yaml`) |
| `75` | Transient failure (API unreachable, rate limited — retry on next fire) |

**Never return `1` for "nothing to do"** — systemd marks the unit failed and alerts.

## What NOT to Do

- Do not invoke `rm-notebooklm run` only when you remember to open a terminal
- Do not attempt to run the pipeline on the reMarkable tablet
- Do not use `rm-notebooklm run` as a Raspberry Pi login script — use a timer

## Prevention

- Any new feature that requires user interaction (confirmations, browser windows,
  interactive prompts) must be confined to one-time setup scripts in `scripts/`,
  not the `run` command
- Systemd/Docker deployment docs (M6-6c, M6-6f) are the canonical deployment guide
- Check: does this feature work with `Type=oneshot` and no TTY? If not, it's a
  setup-script concern, not a pipeline concern

## Related

- `MILESTONES.md:M6-6a,b` — systemd service + timer units
- `MILESTONES.md:M6-6c,d,e,f` — deployment documentation
- `docs/solutions/runtime-errors/concurrent-sync-runs-deadlock-without-filelock.md`
- `docs/solutions/security-issues/google-oauth-token-json-incompatible-with-headless-deployments.md`
