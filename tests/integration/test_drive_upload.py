"""Integration tests for Google Drive upload — uses VCR cassettes."""

from __future__ import annotations

import pytest


@pytest.mark.vcr
def test_upload_text_as_doc_returns_file_id() -> None:
    """upload_text_as_doc() creates a Google Doc and returns file_id."""
    pytest.skip("Milestone 4B: record VCR cassette and implement Drive upload")


@pytest.mark.vcr
def test_delete_file() -> None:
    """delete_file() removes a previously uploaded file."""
    pytest.skip("Milestone 4B: record VCR cassette and implement delete_file")
