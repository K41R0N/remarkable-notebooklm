"""OCR quality tests using jiwer CER/WER metrics.

These tests require an OCR provider API key and are marked with @pytest.mark.ocr.
Run with: pytest tests/unit/test_ocr_quality.py -v -m ocr

Expected text files live in tests/fixtures/expected_text/<name>.txt
Corresponding .rm files live in tests/fixtures/rm_files/<name>.rm
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.ocr

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
RM_FILES_DIR = FIXTURES_DIR / "rm_files"
EXPECTED_DIR = FIXTURES_DIR / "expected_text"

# Add tuples of (rm_filename_stem, expected_text_file_stem) here
KNOWN_HANDWRITING_SAMPLES: list[tuple[str, str]] = [
    # ("handwriting_sample1", "handwriting_sample1"),
    # Add more as fixtures are created
]

KNOWN_TYPED_SAMPLES: list[tuple[str, str]] = [
    # ("typed_sample1", "typed_sample1"),
]


@pytest.mark.parametrize("rm_stem,expected_stem", KNOWN_HANDWRITING_SAMPLES)
def test_ocr_handwriting_quality(rm_stem: str, expected_stem: str) -> None:
    """OCR of handwriting pages should have <10% CER and <15% WER."""
    from jiwer import cer, wer

    from rm_notebooklm.config import settings
    from rm_notebooklm.ocr import get_provider
    from rm_notebooklm.parsing.preprocessor import preprocess_for_ocr

    rm_path = RM_FILES_DIR / f"{rm_stem}.rm"
    expected_path = EXPECTED_DIR / f"{expected_stem}.txt"

    if not rm_path.exists():
        pytest.skip(f"Fixture missing: {rm_path}")
    if not expected_path.exists():
        pytest.skip(f"Expected text missing: {expected_path}")

    expected = expected_path.read_text().strip()

    # Render .rm to PNG (requires rmc to be installed)
    pytest.skip("Milestone 3: implement full OCR pipeline first")

    provider = get_provider(settings.ocr_provider)
    png_bytes = preprocess_for_ocr(rm_path)
    result = provider.transcribe(png_bytes)

    assert cer(expected, result) < 0.10, f"CER too high: {cer(expected, result):.2%}"
    assert wer(expected, result) < 0.15, f"WER too high: {wer(expected, result):.2%}"


@pytest.mark.parametrize("rm_stem,expected_stem", KNOWN_TYPED_SAMPLES)
def test_typed_text_extraction_exact(rm_stem: str, expected_stem: str) -> None:
    """Direct text extraction from typed pages should have 0% CER (exact match)."""
    from jiwer import cer

    from rm_notebooklm.parsing.extractor import extract_typed_text

    rm_path = RM_FILES_DIR / f"{rm_stem}.rm"
    expected_path = EXPECTED_DIR / f"{expected_stem}.txt"

    if not rm_path.exists():
        pytest.skip(f"Fixture missing: {rm_path}")
    if not expected_path.exists():
        pytest.skip(f"Expected text missing: {expected_path}")

    expected = expected_path.read_text().strip()
    pytest.skip("Milestone 2: implement extract_typed_text first")

    result = extract_typed_text(rm_path)
    assert cer(expected, result) == 0.0, (
        f"Typed extraction should be exact, got CER={cer(expected, result):.2%}"
    )
