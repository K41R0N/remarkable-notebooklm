"""Direct text extraction from RootTextBlock (typed pages — no OCR needed)."""

from __future__ import annotations

from pathlib import Path


def extract_typed_text(rm_path: Path) -> str:
    """Extract typed text directly from a .rm file's RootTextBlock.

    Only call this for pages where detect_page_type() returns PageType.TYPED.

    Args:
        rm_path: Path to the .rm binary file.

    Returns:
        Plain text string with preserved line breaks and formatting.
    """
    raise NotImplementedError("Milestone 2: implement typed text extraction")
