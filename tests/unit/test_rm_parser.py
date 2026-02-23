"""Tests for .rm file parsing and page type detection.

All tests use mocked SceneTree objects — no real .rm files required
for unit tests. Real file parsing is covered by integration tests.
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import rmscene

from rm_notebooklm.parsing.rm_parser import ParsedPage, detect_page_type, parse_rm_file

# ---------------------------------------------------------------------------
# Helpers — build lightweight mock trees
# ---------------------------------------------------------------------------


def _make_mock_block(block_type_name: str) -> MagicMock:
    """Create a mock block that passes isinstance() checks for the given type."""
    cls = getattr(rmscene, block_type_name)
    return MagicMock(spec=cls)


def _make_tree(*block_type_names: str) -> MagicMock:
    """Build a mock SceneTree with .blocks containing the specified block types.

    Args:
        block_type_names: rmscene class names to instantiate as mock blocks.

    Returns:
        MagicMock with a .blocks attribute list satisfying isinstance checks.
    """
    blocks = [_make_mock_block(name) for name in block_type_names]
    tree = MagicMock()
    tree.blocks = blocks
    return tree


# ---------------------------------------------------------------------------
# detect_page_type — decision tree
# ---------------------------------------------------------------------------


class TestDetectPageType:
    """Test page content type routing logic with mocked SceneTrees."""

    def test_root_text_block_only_is_typed(self) -> None:
        """RootTextBlock present with no SceneLineItemBlock → 'typed'."""
        tree = _make_tree("RootTextBlock")
        assert detect_page_type(tree) == "typed"

    def test_scene_line_item_block_only_is_handwriting(self) -> None:
        """SceneLineItemBlock present with no RootTextBlock → 'handwriting'."""
        tree = _make_tree("SceneLineItemBlock")
        assert detect_page_type(tree) == "handwriting"

    def test_both_blocks_is_handwriting(self) -> None:
        """Both RootTextBlock and SceneLineItemBlock → 'handwriting' (strokes win)."""
        tree = _make_tree("RootTextBlock", "SceneLineItemBlock")
        assert detect_page_type(tree) == "handwriting"

    def test_stroke_block_first_is_handwriting(self) -> None:
        """SceneLineItemBlock listed first with RootTextBlock → still 'handwriting'."""
        tree = _make_tree("SceneLineItemBlock", "RootTextBlock")
        assert detect_page_type(tree) == "handwriting"

    def test_no_blocks_is_blank(self) -> None:
        """No RootTextBlock and no SceneLineItemBlock → 'blank'."""
        tree = _make_tree()
        assert detect_page_type(tree) == "blank"

    def test_returns_string_literals(self) -> None:
        """Return values are lowercase string literals (not Enum members)."""
        assert isinstance(detect_page_type(_make_tree("RootTextBlock")), str)
        assert isinstance(detect_page_type(_make_tree("SceneLineItemBlock")), str)
        assert isinstance(detect_page_type(_make_tree()), str)


# ---------------------------------------------------------------------------
# parse_rm_file — integration through mocked rmscene.read_tree
# ---------------------------------------------------------------------------


class TestParseRmFile:
    """Tests for parse_rm_file() using a patched rmscene.read_tree."""

    def _patch_read_tree(self, *block_type_names: str):
        """Context manager that patches rmscene.read_tree to return a mock tree."""
        mock_tree = _make_tree(*block_type_names)
        return patch(
            "rm_notebooklm.parsing.rm_parser.rmscene.read_tree",
            return_value=mock_tree,
        )

    def test_typed_page_returns_typed(self) -> None:
        """parse_rm_file() → ParsedPage(page_type='typed') for typed content."""
        with self._patch_read_tree("RootTextBlock"):
            result = parse_rm_file(b"minimal-rm-bytes")
        assert isinstance(result, ParsedPage)
        assert result.page_type == "typed"

    def test_handwriting_page_returns_handwriting(self) -> None:
        """parse_rm_file() → ParsedPage(page_type='handwriting') for strokes."""
        with self._patch_read_tree("SceneLineItemBlock"):
            result = parse_rm_file(b"minimal-rm-bytes")
        assert result.page_type == "handwriting"

    def test_blank_page_returns_blank(self) -> None:
        """parse_rm_file() → ParsedPage(page_type='blank') for empty scene."""
        with self._patch_read_tree():
            result = parse_rm_file(b"minimal-rm-bytes")
        assert result.page_type == "blank"

    def test_mixed_page_is_handwriting(self) -> None:
        """parse_rm_file() with both block types → page_type='handwriting'."""
        with self._patch_read_tree("RootTextBlock", "SceneLineItemBlock"):
            result = parse_rm_file(b"minimal-rm-bytes")
        assert result.page_type == "handwriting"

    def test_raw_bytes_preserved(self) -> None:
        """ParsedPage.raw_bytes equals the input bytes exactly."""
        raw = b"\xde\xad\xbe\xef" * 64
        with self._patch_read_tree("RootTextBlock"):
            result = parse_rm_file(raw)
        assert result.raw_bytes == raw

    def test_tree_stored_on_parsed_page(self) -> None:
        """ParsedPage.tree is the SceneTree object returned by rmscene.read_tree."""
        mock_tree = _make_tree("RootTextBlock")
        with patch(
            "rm_notebooklm.parsing.rm_parser.rmscene.read_tree",
            return_value=mock_tree,
        ):
            result = parse_rm_file(b"minimal-rm-bytes")
        assert result.tree is mock_tree

    def test_empty_bytes_raises_value_error(self) -> None:
        """parse_rm_file() raises ValueError for empty input."""
        with pytest.raises(ValueError, match="rm_bytes must not be empty"):
            parse_rm_file(b"")

    def test_read_tree_receives_bytes_io(self) -> None:
        """parse_rm_file passes a BytesIO object to rmscene.read_tree."""
        mock_tree = _make_tree()
        received: list[object] = []

        def capture_arg(arg: object) -> object:
            received.append(arg)
            return mock_tree

        with patch(
            "rm_notebooklm.parsing.rm_parser.rmscene.read_tree",
            side_effect=capture_arg,
        ):
            parse_rm_file(b"test-bytes")

        assert len(received) == 1
        assert isinstance(received[0], io.BytesIO)


# ---------------------------------------------------------------------------
# Fixture-based tests (skipped if .rm files not present)
# ---------------------------------------------------------------------------


class TestParseRmFileWithFixtures:
    """Integration-style tests using real .rm fixture files.

    These tests are skipped automatically if the fixture files are absent.
    Place sample .rm files in tests/fixtures/rm_files/ to enable them.
    """

    def test_typed_rm_fixture(self, typed_rm_file: Path) -> None:
        """Real typed .rm file parses to page_type == 'typed'."""
        result = parse_rm_file(typed_rm_file.read_bytes())
        assert result.page_type == "typed"

    def test_handwriting_rm_fixture(self, handwriting_rm_file: Path) -> None:
        """Real handwriting .rm file parses to page_type == 'handwriting'."""
        result = parse_rm_file(handwriting_rm_file.read_bytes())
        assert result.page_type == "handwriting"

    def test_blank_rm_fixture(self, blank_rm_file: Path) -> None:
        """Real blank .rm file parses to page_type == 'blank'."""
        result = parse_rm_file(blank_rm_file.read_bytes())
        assert result.page_type == "blank"
