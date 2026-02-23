"""PIL image preprocessing pipeline for OCR.

Pipeline:
  1. Convert to grayscale (keep gradients — do not binarize)
  2. Crop 120px left toolbar + 40px margins on other sides
  3. Boost contrast by 50% for light pencil strokes
  4. Resize to ≤1568px on long edge (prevents Claude server-side resize)
  5. Return as PNG bytes (lossless — preserves stroke edges)

Do NOT:
  - Use JPEG (loses stroke edge sharpness)
  - Binarize (LLMs handle grayscale gradients better)
  - Upscale (226 DPI is sufficient for vision LLMs)
"""

from __future__ import annotations

from pathlib import Path

#: Pixels to crop from the left edge (reMarkable toolbar)
TOOLBAR_CROP_PX = 120

#: Pixels to crop from right/top/bottom edges (margins)
MARGIN_CROP_PX = 40

#: Maximum long edge in pixels (Claude's resize threshold)
MAX_LONG_EDGE_PX = 1568

#: Contrast enhancement factor
CONTRAST_FACTOR = 1.5


def preprocess_for_ocr(image_path: Path) -> bytes:
    """Preprocess a reMarkable PNG render for vision LLM OCR.

    Args:
        image_path: Path to a PNG file rendered from an .rm file.

    Returns:
        Preprocessed PNG as bytes, ready to send to an OCR provider.
    """
    raise NotImplementedError("Milestone 2: implement image preprocessing")
