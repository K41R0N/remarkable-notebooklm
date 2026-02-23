"""Tests for PIL image preprocessing pipeline.

All tests use in-memory images created with PIL — no rmc subprocess needed.
The preprocess_for_ocr() function (which requires rmc) is marked @pytest.mark.slow
and excluded from standard unit test runs.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from rm_notebooklm.parsing.preprocessor import (
    MARGIN_CROP_PX,
    MAX_LONG_EDGE_PX,
    TOOLBAR_CROP_PX,
    preprocess_image,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_png(width: int, height: int, mode: str = "L") -> bytes:
    """Create an in-memory PNG of the given dimensions and mode.

    Args:
        width: Image width in pixels.
        height: Image height in pixels.
        mode: PIL image mode (default "L" = grayscale).

    Returns:
        Raw PNG bytes.
    """
    img = Image.new(mode, (width, height), color=128)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _open_png(png_bytes: bytes) -> Image.Image:
    """Open PNG bytes with PIL and return the Image object."""
    return Image.open(io.BytesIO(png_bytes))


# ---------------------------------------------------------------------------
# preprocess_image — PIL pipeline (no subprocess)
# ---------------------------------------------------------------------------


class TestPreprocessImage:
    """Test the PIL preprocessing pipeline via preprocess_image()."""

    # --- Output format ---

    def test_output_is_bytes(self) -> None:
        """preprocess_image() returns bytes."""
        png = _make_png(1404, 1872)
        result = preprocess_image(png)
        assert isinstance(result, bytes)

    def test_output_is_png(self) -> None:
        """preprocess_image() output starts with PNG magic bytes (\\x89PNG)."""
        png = _make_png(1404, 1872)
        result = preprocess_image(png)
        assert result[:4] == b"\x89PNG"

    def test_output_is_grayscale(self) -> None:
        """preprocess_image() converts input to grayscale (PIL mode 'L')."""
        # Start with an RGB image — should become L
        rgb_png = _make_png(800, 600, mode="RGB")
        result = preprocess_image(rgb_png)
        out = _open_png(result)
        assert out.mode == "L"

    def test_grayscale_input_stays_grayscale(self) -> None:
        """preprocess_image() keeps an already-grayscale image as mode 'L'."""
        gray_png = _make_png(800, 600, mode="L")
        result = preprocess_image(gray_png)
        out = _open_png(result)
        assert out.mode == "L"

    # --- Long edge resize ---

    def test_large_image_resized_to_max_long_edge(self) -> None:
        """Images with long edge > 1568px are downscaled to exactly ≤1568px."""
        # reMarkable full page: 1404 × 1872, long edge = 1872 > 1568
        png = _make_png(1404, 1872)
        result = preprocess_image(png)
        out = _open_png(result)
        assert max(out.size) <= MAX_LONG_EDGE_PX

    def test_very_large_image_resized(self) -> None:
        """Explicitly large image (1700 × 2267) has long edge ≤ 1568px after processing."""
        png = _make_png(1700, 2267)
        result = preprocess_image(png)
        out = _open_png(result)
        assert max(out.size) <= MAX_LONG_EDGE_PX

    def test_small_image_not_upscaled(self) -> None:
        """Images with long edge ≤ 1568px are NOT resized (no upscaling)."""
        # 500 × 700 → long edge 700 ≤ 1568: must stay unchanged (modulo crop)
        # After toolbar (120) + margin (40 each) crop from 500 × 700:
        # width: 500 - 120 - 40 - 40 = 300; height: 700 - 40 - 40 = 620
        png = _make_png(500, 700)
        result = preprocess_image(png)
        out = _open_png(result)
        # Long edge must NOT exceed what was left after cropping
        assert max(out.size) <= max(500, 700)

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
        post_crop_w = width - TOOLBAR_CROP_PX - 2 * MARGIN_CROP_PX
        post_crop_h = height - 2 * MARGIN_CROP_PX
        crop_ratio = post_crop_w / post_crop_h
        result_ratio = out_w / out_h
        # Allow 2% tolerance for integer rounding during resize
        assert abs(result_ratio - crop_ratio) / crop_ratio < 0.02

    # --- Toolbar crop ---

    def test_toolbar_crop_reduces_width(self) -> None:
        """Output width is less than input width due to toolbar crop."""
        # Use a wide image so the crop is measurable
        png = _make_png(400, 300)  # Wide, so post-crop won't hit minimum
        result = preprocess_image(png)
        out = _open_png(result)
        # Toolbar (120) + margin (40) = 160 from left, margin (40) from right
        # Expected width: 400 - 120 - 40 - 40 = 200
        assert out.size[0] < 400

    def test_toolbar_crop_correct_amount(self) -> None:
        """Width decreases by exactly TOOLBAR_CROP_PX + 2 * MARGIN_CROP_PX."""
        width, height = 600, 800
        # Post-crop: width - 120 - 40 (left margin) - 40 (right margin) = 360
        expected_w = width - TOOLBAR_CROP_PX - 2 * MARGIN_CROP_PX
        # Post-crop: height - 40 (top) - 40 (bottom) = 720
        expected_h = height - 2 * MARGIN_CROP_PX
        png = _make_png(width, height)
        result = preprocess_image(png)
        out = _open_png(result)
        # Long edge: 720 ≤ 1568, so no resize occurs
        assert out.size == (expected_w, expected_h)

    # --- Margin crop ---

    def test_margin_crop_reduces_height(self) -> None:
        """Output height is less than input height due to margin crop."""
        png = _make_png(600, 800)
        result = preprocess_image(png)
        out = _open_png(result)
        assert out.size[1] < 800

    # --- Edge cases ---

    def test_empty_bytes_raises_value_error(self) -> None:
        """preprocess_image() raises ValueError for empty input."""
        with pytest.raises(ValueError, match="png_bytes must not be empty"):
            preprocess_image(b"")

    def test_non_empty_result_for_small_input(self) -> None:
        """preprocess_image() produces non-empty output even for small images."""
        # Minimum useful image: just large enough for the crops
        # toolbar (120) + margin_left (40) + 1px content + margin_right (40) = 201
        # height: margin_top (40) + 1px + margin_bottom (40) = 81
        png = _make_png(300, 200)
        result = preprocess_image(png)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# preprocess_for_ocr — requires rmc subprocess (marked slow)
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestPreprocessForOcr:
    """Tests for preprocess_for_ocr() — requires rmc to be installed.

    These are excluded from standard unit test runs:
        pytest tests/unit/ -v  # slow tests skipped
        pytest tests/unit/ -v -m slow  # slow tests only
    """

    def test_empty_bytes_raises_value_error(self) -> None:
        """preprocess_for_ocr() raises ValueError for empty rm_bytes."""
        from rm_notebooklm.parsing.preprocessor import preprocess_for_ocr

        with pytest.raises(ValueError, match="rm_bytes must not be empty"):
            preprocess_for_ocr(b"")

    def test_unsupported_renderer_raises_value_error(self) -> None:
        """preprocess_for_ocr() raises ValueError for unknown renderer name."""
        from rm_notebooklm.parsing.preprocessor import preprocess_for_ocr

        with pytest.raises(ValueError, match="Unsupported renderer"):
            preprocess_for_ocr(b"fake", renderer="inkscape")
