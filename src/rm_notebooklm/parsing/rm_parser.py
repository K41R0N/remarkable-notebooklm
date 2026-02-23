"""rmscene wrapper — parse .rm files and detect page content type.

Decision tree per page:
  - RootTextBlock present + no SceneLineItemBlock → "typed"
  - SceneLineItemBlock present → "handwriting"
  - Neither → "blank" (skip)
"""

from __future__ import annotations

import io
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

import rmscene
from rmscene import SceneTree

from rm_notebooklm.utils.logging import get_logger

log = get_logger(__name__)

PageType = Literal["typed", "handwriting", "blank"]


@dataclass
class ParsedPage:
    """Result of parsing a single .rm file page."""

    page_type: PageType
    tree: SceneTree
    raw_bytes: bytes


def _iter_blocks(tree: SceneTree) -> Iterator[Any]:
    """Yield all top-level blocks from the scene tree.

    rmscene.SceneTree exposes blocks differently across sub-versions.
    We try the known attributes in order.
    """
    # rmscene 0.7.x: SceneTree has a .root attribute which is a SceneGlyphItemBlock
    # or SceneGroupItemBlock with .children, and .blocks at the top level.
    if hasattr(tree, "blocks"):
        yield from tree.blocks
    elif hasattr(tree, "root") and hasattr(tree.root, "children"):
        yield from tree.root.children
    else:
        # Fallback: tree itself may be iterable
        yield from tree


def detect_page_type(tree: SceneTree) -> PageType:
    """Detect the content type of a parsed SceneTree.

    Decision tree:
      - ``SceneLineItemBlock`` present (regardless of text blocks) → ``"handwriting"``
      - ``RootTextBlock`` present AND no ``SceneLineItemBlock`` → ``"typed"``
      - Neither present → ``"blank"``

    Args:
        tree: A parsed rmscene SceneTree (from ``read_tree()``).

    Returns:
        One of ``"typed"``, ``"handwriting"``, or ``"blank"``.
    """
    has_text_block = False
    has_stroke_block = False

    for block in _iter_blocks(tree):
        if isinstance(block, rmscene.SceneLineItemBlock):
            has_stroke_block = True
            break
        if isinstance(block, rmscene.RootTextBlock):
            has_text_block = True

    if has_stroke_block:
        log.debug(
            "detect_page_type",
            result="handwriting",
            reason="SceneLineItemBlock found",
        )
        return "handwriting"
    if has_text_block:
        log.debug(
            "detect_page_type",
            result="typed",
            reason="RootTextBlock found, no strokes",
        )
        return "typed"
    log.debug(
        "detect_page_type",
        result="blank",
        reason="no RootTextBlock and no SceneLineItemBlock",
    )
    return "blank"


def parse_rm_file(rm_bytes: bytes) -> ParsedPage:
    """Parse raw .rm file bytes and determine page content type.

    Args:
        rm_bytes: Raw bytes of a ``.rm`` binary file (v6 format, firmware 3.x+).

    Returns:
        A :class:`ParsedPage` with the detected page type, the parsed
        :class:`rmscene.SceneTree`, and the original raw bytes.

    Raises:
        ValueError: If ``rm_bytes`` is empty.
        Exception: Propagates any rmscene parse errors for the caller to handle.
    """
    if not rm_bytes:
        raise ValueError("rm_bytes must not be empty")

    log.debug("parse_rm_file", bytes_len=len(rm_bytes))
    tree: SceneTree = rmscene.read_tree(io.BytesIO(rm_bytes))
    page_type = detect_page_type(tree)
    log.info("parse_rm_file_complete", page_type=page_type)
    return ParsedPage(page_type=page_type, tree=tree, raw_bytes=rm_bytes)
