"""Integration tests for NotebookLM Enterprise API — uses VCR cassettes."""

from __future__ import annotations

import pytest


@pytest.mark.vcr
def test_create_notebook() -> None:
    """create_notebook() returns a notebook resource ID."""
    pytest.skip("Milestone 4B: record VCR cassette and implement create_notebook")


@pytest.mark.vcr
def test_add_source_file() -> None:
    """add_source_file() uploads a text file and returns a source ID."""
    pytest.skip("Milestone 4B: record VCR cassette and implement add_source_file")
