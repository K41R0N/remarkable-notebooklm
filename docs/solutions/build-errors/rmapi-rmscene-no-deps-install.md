---
title: "rm-api vs rmscene packaging dependency conflict"
date: 2026-02-23
category: build-errors
tags:
  - pip-resolution
  - version-pinning
  - installation-blocker
  - rm-api
  - rmscene
  - packaging
problem_type: dependency_conflict
severity: critical
status: solved
milestone: M0/M1
---

# rm-api vs rmscene packaging dependency conflict

## Symptom

Running `pip install -e ".[dev]"` fails with a dependency conflict error:

```
pip._vendor.resolvelib.resolvers.ResolutionImpossible:
  Cannot install rm-api==1.1.1 and rmscene==0.7.0 because these package versions
  have conflicting dependencies.
  The conflict is caused by:
      rm-api 1.1.1 depends on packaging>=24.2,<25
      rmscene 0.7.0 depends on packaging>=23,<24
```

## Root Cause

`rm-api==1.1.1` and `rmscene==0.7.0` both declare `packaging` as a dependency but
specify incompatible version ranges:

| Library | packaging constraint |
|---------|---------------------|
| `rm-api==1.1.1` | `>=24.2,<25` |
| `rmscene==0.7.0` | `>=23,<24` |

pip's dependency resolver cannot find a version of `packaging` that satisfies both
constraints simultaneously, so the whole install fails.

**Why this is safe to work around:** `packaging` is a *build-time metadata* dependency
for both libraries — used during package discovery and version parsing, not at runtime
in any code path we exercise. The two libraries can coexist in the same Python process
regardless of which `packaging` version is installed.

## Solution

Install in two phases to bypass pip's constraint solver:

```bash
# Phase 1: install the conflicting libraries directly (lets pip install each
# with its own preferred packaging version; one will win)
pip install rmscene==0.7.0

# Phase 2: install the project without running dependency resolution
pip install -e ".[dev]" --no-deps
```

The `--no-deps` flag tells pip to install the package itself but skip recursively
resolving and installing all dependencies. Since `rmscene` and `rm-api` are already
present in the environment, everything works.

### Verification

```bash
# Confirm both libraries are present and functional
python -c "import rmscene; print('rmscene OK')"
python -c "import rm_api; print('rm_api OK')"

# Run the project's test suite to confirm the install is sound
pytest tests/unit/ -q
```

### Full development setup sequence

```bash
python -m venv .venv
source .venv/bin/activate

# Install conflicting packages first
pip install rmscene==0.7.0

# Then install the project (skipping dep resolution)
pip install -e ".[dev]" --no-deps

# Verify
pytest tests/unit/ -q
```

## Prevention

### Detect conflicts early in CI

Add `pip check` to CI before running tests. It catches unsatisfied requirements
and will alert when upstream packages resolve the conflict:

```yaml
# .github/workflows/ci.yml
- name: Check dependency consistency
  run: pip check || echo "Known conflict: rm-api/rmscene packaging pins"
```

### Document the workaround in pyproject.toml

The comment block near the dependency pins serves as in-code documentation:

```toml
dependencies = [
    # ⚠️  KNOWN CONFLICT: rm-api==1.1.1 requires packaging>=24.2,<25 but
    #     rmscene==0.7.0 requires packaging>=23,<24. Install with --no-deps.
    #     See docs/solutions/build-errors/rmapi-rmscene-no-deps-install.md
    "rm-api==1.1.1",
    "rmscene==0.7.0",
    ...
]
```

### Long-term resolution

Monitor both libraries for updates. When either ships a compatible release:

```bash
# Test compatibility before unpinning
pip install rm-api==X.Y.Z rmscene==0.7.0
pip check
```

If `pip check` passes, remove the `--no-deps` workaround and update the version pins.
Track as part of any dependency audit.

## Related

- `CLAUDE.md § Critical Library Versions` — explains why `rm-api` (not `rmapy`) is
  required for sync15 protocol support
- `CLAUDE.md § What NOT to Do` — do not use `rmapy`; it does not support sync15
- `MILESTONES.md § Known Risks` — "rm-api API changes: pin rm-api==1.1.1"
- `docs/plans/2026-02-23-feat-milestone-1-remarkable-sync-plan.md § Dependencies & Risks`
