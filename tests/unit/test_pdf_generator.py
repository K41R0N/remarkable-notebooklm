"""Tests for reMarkable-formatted PDF generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from rm_notebooklm.pdf.constants import (
    MAX_FILE_SIZE_BYTES,
    RM2_HEIGHT_PT,
    RM2_WIDTH_PT,
)


class TestRemarkablePDFGenerator:
    """Test PDF output properties."""

    def test_output_is_valid_pdf(self, tmp_path: Path) -> None:
        """Generated file is a valid PDF (starts with %PDF header)."""
        pytest.skip("Milestone 5: implement PDF generator first")
        from rm_notebooklm.pdf.generator import RemarkablePDFGenerator

        gen = RemarkablePDFGenerator()
        output = tmp_path / "test.pdf"
        gen.generate("Hello reMarkable", output)

        assert output.exists()
        with open(output, "rb") as f:
            assert f.read(4) == b"%PDF"

    def test_page_size_is_remarkable_dimensions(self, tmp_path: Path) -> None:
        """PDF page size matches reMarkable 2 dimensions (447.3 × 596.4 pt)."""
        pytest.skip("Milestone 5: implement PDF generator first")
        from pypdf import PdfReader

        from rm_notebooklm.pdf.generator import RemarkablePDFGenerator

        gen = RemarkablePDFGenerator()
        output = tmp_path / "dimensions.pdf"
        gen.generate("Test content", output)

        reader = PdfReader(output)
        page = reader.pages[0]
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)

        assert abs(width - RM2_WIDTH_PT) < 0.5, f"Width {width} != {RM2_WIDTH_PT}"
        assert abs(height - RM2_HEIGHT_PT) < 0.5, f"Height {height} != {RM2_HEIGHT_PT}"

    def test_file_size_within_limit_for_large_text(self, tmp_path: Path) -> None:
        """10,000 word document stays under 100MB limit."""
        pytest.skip("Milestone 5: implement PDF generator first")
        from rm_notebooklm.pdf.generator import RemarkablePDFGenerator

        gen = RemarkablePDFGenerator()
        large_text = "The quick brown fox jumps over the lazy dog. " * 10000
        output = tmp_path / "large.pdf"
        gen.generate(large_text, output)

        assert output.stat().st_size < MAX_FILE_SIZE_BYTES

    def test_raises_on_exceeding_size_limit(self, tmp_path: Path) -> None:
        """ValueError raised when content would exceed 100MB."""
        pytest.skip("Milestone 5: implement PDF generator first")
        from rm_notebooklm.pdf.generator import RemarkablePDFGenerator

        RemarkablePDFGenerator()
        # This test would require mocking the size check
        pytest.xfail("Requires mock for size limit enforcement")
