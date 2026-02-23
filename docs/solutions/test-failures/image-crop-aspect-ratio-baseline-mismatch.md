---
title: "Image pipeline aspect ratio test fails — comparing output to pre-crop input dimensions"
type: test-failure
severity: test-suite-blocking
component: preprocessing
milestone: M2
date: 2026-02-24
tags: [PIL, image-processing, aspect-ratio, test-baseline, preprocessor, pytest]
---

# Image pipeline aspect ratio test fails — comparing output to pre-crop input dimensions

## Problem Symptom

`test_aspect_ratio_maintained_after_resize` fails with a large discrepancy even though
the implementation is correct:

```
FAILED tests/unit/test_preprocessor.py::TestPreprocessImage::test_aspect_ratio_maintained_after_resize
AssertionError: assert (0.0784 / 0.75) < 0.05
```

Output ratio (~0.6715) vs expected ratio (~0.75) → ~10% error, well above any rounding tolerance.

## Root Cause

The pipeline in `preprocess_image()` runs these steps **in order**:

```
Step 1: Convert to grayscale (no dimension change)
Step 2: Crop left toolbar — remove TOOLBAR_CROP_PX (120px) from left
Step 3: Crop margins     — remove MARGIN_CROP_PX (40px) from each edge
Step 4: Resize           — if long_edge > MAX_LONG_EDGE_PX (1568px)
```

The **crop steps change the aspect ratio** before the resize step runs.

The original (incorrect) test compared the final output ratio to the *original* input dimensions:

```python
# ❌ WRONG — crops already changed the ratio before resize
original_ratio = width / height   # e.g. 1404 / 1872 = 0.75
result_ratio   = out_w / out_h    # e.g. 1204 / 1792 * scale = ~0.6715
# These will NEVER match because crop changed the ratio
assert abs(result_ratio - original_ratio) / original_ratio < 0.05
```

The resize step preserves the **post-crop** ratio, not the original input ratio.

## Working Solution

Compute the expected post-crop dimensions first, then compare output to *that* baseline:

```python
def test_aspect_ratio_maintained_after_resize(self) -> None:
    """Resize step preserves the post-crop aspect ratio (within rounding)."""
    width, height = 1404, 1872
    png = _make_png(width, height)
    result = preprocess_image(png)
    out = _open_png(result)
    out_w, out_h = out.size

    # Compare against the post-crop ratio, not the original input ratio.
    # Cropping (toolbar + margins) changes the aspect ratio; the resize step
    # must preserve *that* ratio, not the original.
    post_crop_w = width - TOOLBAR_CROP_PX - 2 * MARGIN_CROP_PX  # 1404 - 120 - 80 = 1204
    post_crop_h = height - 2 * MARGIN_CROP_PX                   # 1872 - 80 = 1792
    crop_ratio = post_crop_w / post_crop_h                       # ~0.6719
    result_ratio = out_w / out_h

    # Allow 2% tolerance for integer rounding during resize
    assert abs(result_ratio - crop_ratio) / crop_ratio < 0.02
```

## General Rule for Multi-Step Image Pipeline Tests

When testing pipelines with sequential transformations, the baseline for each assertion
must match the **state of the image at that pipeline stage**, not the original input:

```
Input:            1404 × 1872  (ratio: 0.750)
  ↓ crop toolbar + margins
Post-crop:        1204 × 1792  (ratio: 0.672)  ← USE THIS for resize ratio test
  ↓ resize if long_edge > 1568px
Output:           ~1054 × 1568 (ratio: ~0.672)
```

| What you're testing | Baseline to compare against |
|---------------------|-----------------------------|
| Resize preserves ratio | Post-crop dimensions |
| Output size ≤ MAX_LONG_EDGE_PX | MAX_LONG_EDGE_PX constant |
| Crop reduces width | Post-crop width = input - TOOLBAR - 2×MARGIN |
| Crop reduces height | Post-crop height = input - 2×MARGIN |

## Red Flag Patterns (Code Review)

- Test comparing `output_ratio` directly to `input_w / input_h` when pipeline has crop steps
- ~10–15% discrepancy in aspect ratio assertions (characteristic of toolbar crop being ignored)
- Comments like "aspect ratio should be width/height of original image"
- Using original input dimensions as expected values for any dimension after a crop operation

## Mathematical Formulas

For this project's pipeline constants:

```python
post_crop_w = input_w - TOOLBAR_CROP_PX - 2 * MARGIN_CROP_PX
post_crop_h = input_h - 2 * MARGIN_CROP_PX
# Where: TOOLBAR_CROP_PX = 120, MARGIN_CROP_PX = 40
```

## Files Affected in This Project

| File | Line | Fix Applied |
|------|------|-------------|
| `tests/unit/test_preprocessor.py` | 114–129 | Compare to `post_crop_w / post_crop_h` |

## References

- `src/rm_notebooklm/parsing/preprocessor.py` — preprocess_image() pipeline (Steps 2–4)
- `tests/unit/test_preprocessor.py` — test_aspect_ratio_maintained_after_resize()
- `docs/solutions/build-errors/pil-image-open-strict-type-annotation.md` — companion M2 fix
