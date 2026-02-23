"""Direct text extraction from RootTextBlock (typed pages — no OCR needed)."""

from __future__ import annotations

import rmscene
from rmscene import SceneTree

from rm_notebooklm.utils.logging import get_logger

log = get_logger(__name__)


def extract_typed_text(tree: SceneTree) -> str:
    """Extract typed text directly from a SceneTree's RootTextBlock.

    Walks the ``RootTextBlock`` → ``CrdtSequence`` → extracts character values
    in order. Only call this for pages where ``detect_page_type()`` returns
    ``"typed"``.

    Args:
        tree: A parsed rmscene SceneTree containing a RootTextBlock.

    Returns:
        Plain text string, stripped of leading/trailing whitespace.
        Returns ``""`` if no RootTextBlock is found or if the CrdtSequence
        is empty.
    """
    # Import here to avoid a top-level circular dependency between extractor
    # and rm_parser (both live in the same package).
    from rm_notebooklm.parsing.rm_parser import _iter_blocks

    for block in _iter_blocks(tree):
        if not isinstance(block, rmscene.RootTextBlock):
            continue

        # RootTextBlock.items is a CrdtSequence of CrdtSequenceItem[str]
        chars: list[str] = []
        sequence = block.items
        for item in sequence:
            # CrdtSequenceItem has a .value attribute
            val = item.value
            if val is not None:
                chars.append(str(val))

        text = "".join(chars).strip()
        log.debug("extract_typed_text", char_count=len(text))
        return text

    log.debug("extract_typed_text", char_count=0, reason="no RootTextBlock found")
    return ""
