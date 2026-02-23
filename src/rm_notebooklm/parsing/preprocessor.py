"""PIL image preprocessing pipeline for OCR.

Pipeline:
  1. Render .rm bytes to PNG via ``rmc`` subprocess (for handwriting pages)
  2. Convert to grayscale (keep gradients — do not binarize)
  3. Crop 120px left toolbar
  4. Crop 40px margins on remaining edges
  5. Resize to ≤1568px on long edge only if larger (no upscaling)
  6. Return as PNG bytes (lossless — preserves stroke edges)

Do NOT:
  - Use JPEG (loses stroke edge sharpness)
  - Binarize (LLMs handle grayscale gradients better)
  - Upscale (226 DPI is sufficient for vision LLMs)
"""

from __future__ import annotations

import io
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from rm_notebooklm.utils.logging import get_logger

log = get_logger(__name__)

#: Pixels to crop from the left edge (reMarkable toolbar)
TOOLBAR_CROP_PX = 120

#: Pixels to crop from right/top/bottom edges (margins)
MARGIN_CROP_PX = 40

#: Maximum long edge in pixels (prevents server-side resize in Claude / other LLMs)
MAX_LONG_EDGE_PX = 1568


def preprocess_image(png_bytes: bytes) -> bytes:
    """Apply the PIL preprocessing pipeline to already-rendered PNG bytes.

    Use this when a PNG is already available (e.g., from rmc output or a test
    fixture). For raw ``.rm`` bytes, use :func:`preprocess_for_ocr` instead.

    Pipeline steps:
      1. Open with PIL
      2. Convert to grayscale ("L" mode)
      3. Crop left toolbar (first ``TOOLBAR_CROP_PX`` columns)
      4. Crop ``MARGIN_CROP_PX`` from each remaining edge
      5. Resize so long edge ≤ ``MAX_LONG_EDGE_PX`` (only if larger — never upscale)

    Args:
        png_bytes: Raw PNG bytes to preprocess.

    Returns:
        Preprocessed grayscale PNG as bytes.

    Raises:
        ValueError: If ``png_bytes`` is empty.
    """
    if not png_bytes:
        raise ValueError("png_bytes must not be empty")

    image: Image.Image = Image.open(io.BytesIO(png_bytes))

    # Step 1: Convert to grayscale — do NOT binarize
    image = image.convert("L")

    width, height = image.size
    log.debug("preprocess_image_start", width=width, height=height, mode=image.mode)

    # Step 2: Crop left toolbar (120px)
    if width > TOOLBAR_CROP_PX:
        image = image.crop((TOOLBAR_CROP_PX, 0, width, height))
        width, height = image.size

    # Step 3: Crop margins (40px each side)
    left = MARGIN_CROP_PX
    top = MARGIN_CROP_PX
    right = max(width - MARGIN_CROP_PX, left + 1)
    bottom = max(height - MARGIN_CROP_PX, top + 1)
    image = image.crop((left, top, right, bottom))
    width, height = image.size

    # Step 4: Resize to ≤1568px on long edge — only downscale, never upscale
    long_edge = max(width, height)
    if long_edge > MAX_LONG_EDGE_PX:
        scale = MAX_LONG_EDGE_PX / long_edge
        new_width = max(1, int(width * scale))
        new_height = max(1, int(height * scale))
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        log.debug(
            "preprocess_image_resized",
            from_size=(width, height),
            to_size=(new_width, new_height),
        )

    # Step 5: Encode to PNG bytes
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    result = buf.getvalue()
    log.debug("preprocess_image_complete", output_bytes=len(result))
    return result


def preprocess_for_ocr(rm_bytes: bytes, renderer: str = "rmc") -> bytes:
    """Render a ``.rm`` file to PNG and apply the OCR preprocessing pipeline.

    Uses ``rmc`` as a subprocess renderer to convert the binary ``.rm`` format
    to a PNG, then passes the output through :func:`preprocess_image`.

    ``rmc`` CLI usage::

        rmc -t png -o <output_dir> <input.rm>

    Args:
        rm_bytes: Raw bytes of a ``.rm`` binary file.
        renderer: Renderer to use. Currently only ``"rmc"`` is supported.

    Returns:
        Preprocessed grayscale PNG as bytes, ready to send to an OCR provider.

    Raises:
        ValueError: If ``rm_bytes`` is empty or renderer is unsupported.
        RuntimeError: If the ``rmc`` subprocess fails.
        FileNotFoundError: If no PNG output was produced by rmc.
    """
    if not rm_bytes:
        raise ValueError("rm_bytes must not be empty")
    if renderer != "rmc":
        raise ValueError(f"Unsupported renderer: {renderer!r}. Only 'rmc' is supported.")

    log.debug("preprocess_for_ocr", bytes_len=len(rm_bytes), renderer=renderer)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        rm_file = tmp_path / "page.rm"
        rm_file.write_bytes(rm_bytes)

        proc = subprocess.run(
            ["rmc", "-t", "png", "-o", str(tmp_path), str(rm_file)],
            capture_output=True,
            timeout=30,
        )
        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"rmc renderer failed (exit {proc.returncode}): {stderr}")

        # rmc writes output as <input_name>.png or <input_name>-0.png etc.
        png_candidates = sorted(tmp_path.glob("*.png"))
        if not png_candidates:
            raise FileNotFoundError(
                f"rmc produced no PNG output in {tmp_path}. "
                f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
            )

        # Read bytes while the temp dir is still alive, before cleanup.
        png_path = png_candidates[0]
        rendered_png = png_path.read_bytes()
        log.debug(
            "preprocess_for_ocr_rmc_done",
            png_path=str(png_path),
            rendered_bytes=len(rendered_png),
        )
        return preprocess_image(rendered_png)
