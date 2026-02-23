"""Tests for PIL image preprocessing pipeline."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from rm_notebooklm.parsing.preprocessor import (
    MAX_LONG_EDGE_PX,
    TOOLBAR_CROP_PX,
    preprocess_for_ocr,
)


def make_test_image(width: int = 1404, height: int = 1872) -> Path:
    """Create a synthetic reMarkable-sized grayscale PNG for testing."""
    img = Image.new("L", (width, height), color=255)
    # Draw a fake toolbar region (darker)
    for x in range(TOOLBAR_CROP_PX):
        for y in range(height):
            img.putpixel((x, y), 200)
    return img


class TestPreprocessForOCR:
    """Test image preprocessing pipeline output properties."""

    def test_output_is_png_bytes(self, tmp_path: Path) -> None:
        """preprocess_for_ocr returns valid PNG bytes."""
        pytest.skip("Milestone 2: implement preprocess_for_ocr first")
        img = make_test_image()
        img_path = tmp_path / "test.png"
        img.save(img_path)

        result = preprocess_for_ocr(img_path)
        assert isinstance(result, bytes)
        # PNG magic bytes: \x89PNG
        assert result[:4] == b"\x89PNG"

    def test_output_dimensions_within_limit(self, tmp_path: Path) -> None:
        """Output image long edge is ≤1568px (Claude resize threshold)."""
        pytest.skip("Milestone 2: implement preprocess_for_ocr first")
        img = make_test_image(width=1404, height=1872)
        img_path = tmp_path / "full_size.png"
        img.save(img_path)

        result = preprocess_for_ocr(img_path)
        output_img = Image.open(io.BytesIO(result))
        assert max(output_img.size) <= MAX_LONG_EDGE_PX

    def test_output_is_grayscale(self, tmp_path: Path) -> None:
        """Output image is grayscale (mode L or RGB within tolerance)."""
        pytest.skip("Milestone 2: implement preprocess_for_ocr first")
        img = make_test_image()
        img_path = tmp_path / "color.png"
        img.save(img_path)

        result = preprocess_for_ocr(img_path)
        output_img = Image.open(io.BytesIO(result))
        assert output_img.mode == "L"

    def test_toolbar_region_cropped(self, tmp_path: Path) -> None:
        """Output image width is less than input width (toolbar cropped)."""
        pytest.skip("Milestone 2: implement preprocess_for_ocr first")
        img = make_test_image(width=1404, height=1872)
        img_path = tmp_path / "original.png"
        img.save(img_path)

        result = preprocess_for_ocr(img_path)
        output_img = Image.open(io.BytesIO(result))
        # Width should be reduced by at least TOOLBAR_CROP_PX
        assert output_img.size[0] < 1404
