---
title: "PIL Image.open() returns ImageFile, not Image.Image — mypy strict assignment error"
type: build-error
severity: ci-blocking
component: preprocessing
milestone: M2
date: 2026-02-24
tags: [PIL, Pillow, mypy, type-annotation, preprocessor]
---

# PIL `Image.open()` returns `ImageFile`, not `Image.Image` — mypy strict assignment error

## Problem Symptom

Running `mypy src/` under `strict = true` emits `Incompatible types in assignment` errors
on every line that reassigns the result of `Image.open()` to the same variable:

```
src/rm_notebooklm/parsing/preprocessor.py:68: error: Incompatible types in assignment
    (expression has type "Image", variable has type "ImageFile")
src/rm_notebooklm/parsing/preprocessor.py:75: error: Incompatible types in assignment
src/rm_notebooklm/parsing/preprocessor.py:83: error: Incompatible types in assignment
src/rm_notebooklm/parsing/preprocessor.py:92: error: Incompatible types in assignment
```

This blocks CI on every pipeline run until fixed.

## Root Cause

`PIL.Image.open()` is typed to return `PIL.ImageFile.ImageFile`, a subclass of `Image.Image`.
When you write bare:

```python
image = Image.open(io.BytesIO(png_bytes))   # inferred: ImageFile.ImageFile
image = image.convert("L")                  # returns: Image.Image
# mypy strict: cannot assign Image.Image to ImageFile.ImageFile → ERROR
```

mypy infers the variable type from the first assignment (`ImageFile.ImageFile`) and then rejects
the `.convert()` / `.crop()` / `.resize()` returns (which are `Image.Image`) as incompatible.

## Working Solution

Declare the variable as `Image.Image` at the point of `Image.open()`:

```python
# preprocessor.py — the correct pattern
image: Image.Image = Image.open(io.BytesIO(png_bytes))
image = image.convert("L")         # Image.Image — ✓
image = image.crop((left, top, right, bottom))  # Image.Image — ✓
image = image.resize((w, h), Image.Resampling.LANCZOS)  # Image.Image — ✓
```

The explicit annotation tells mypy the variable holds `Image.Image`, and all subsequent
method chains (`convert`, `crop`, `resize`) return `Image.Image`, so reassignments type-check.

## What NOT to Do

```python
# ❌ bare assignment — mypy strict will reject later reassignments
image = Image.open(io.BytesIO(png_bytes))

# ❌ type: ignore — masks real errors and makes CI noisy
image = Image.open(io.BytesIO(png_bytes))  # type: ignore[assignment]

# ❌ adding PIL to mypy ignore_missing_imports — Pillow has correct inline types;
#    suppressing would hide real future errors
```

Do NOT add `PIL` or `PIL.*` to the `[[tool.mypy.overrides]]` block in `pyproject.toml`.
Pillow ships with accurate PEP 561 inline stubs. The pattern above is the correct fix.

## Red Flag Patterns (Code Review)

- Any `image = Image.open(...)` without a preceding `image: Image.Image =` annotation
- `# type: ignore` on PIL method calls (signals the symptom was masked, not fixed)
- `type: ignore[misc]` on `yield from tree` or similar — unused `type: ignore` comments also
  fail mypy strict (`Unused "type: ignore" comment`)

## Files Affected in This Project

| File | Line | Fix Applied |
|------|------|-------------|
| `src/rm_notebooklm/parsing/preprocessor.py` | 65 | `image: Image.Image = Image.open(...)` |

## Prevention

Add this to code review checklist for any PIL image processing function:

- [ ] `Image.open()` assigned with explicit `image: Image.Image = ...` annotation
- [ ] No `# type: ignore` comments on PIL method calls
- [ ] Test helper functions returning PIL images annotated with `-> Image.Image`

## References

- Pillow source: `PIL/ImageFile.py` — `ImageFile` extends `Image.Image`
- `src/rm_notebooklm/parsing/preprocessor.py` — preprocess_image() function
- `tests/unit/test_preprocessor.py` — `_open_png()` helper returns `Image.Image`
- `pyproject.toml` — `[tool.mypy]` strict = true configuration
