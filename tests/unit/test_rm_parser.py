"""Tests for .rm file parsing and page type detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from rm_notebooklm.parsing.rm_parser import PageType, detect_page_type


class TestDetectPageType:
    """Test page content type routing logic."""

    def test_typed_page_returns_typed(self, typed_rm_file: Path) -> None:
        """Pages with only RootTextBlock return PageType.TYPED."""
        pytest.skip("Milestone 2: implement detect_page_type first")
        result = detect_page_type(typed_rm_file)
        assert result == PageType.TYPED

    def test_handwriting_page_returns_handwriting(self, handwriting_rm_file: Path) -> None:
        """Pages with SceneLineItemBlock return PageType.HANDWRITING."""
        pytest.skip("Milestone 2: implement detect_page_type first")
        result = detect_page_type(handwriting_rm_file)
        assert result == PageType.HANDWRITING

    def test_blank_page_returns_blank(self, blank_rm_file: Path) -> None:
        """Pages with no content blocks return PageType.BLANK."""
        pytest.skip("Milestone 2: implement detect_page_type first")
        result = detect_page_type(blank_rm_file)
        assert result == PageType.BLANK
