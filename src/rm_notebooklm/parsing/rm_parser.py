"""rmscene wrapper — parse .rm files and detect page content type.

Decision tree per page:
  - RootTextBlock present + no SceneLineItemBlock → PageType.TYPED
  - SceneLineItemBlock present → PageType.HANDWRITING
  - Neither → PageType.BLANK (skip)
"""

from __future__ import annotations

from enum import Enum, auto
from pathlib import Path


class PageType(Enum):
    """Content type of a parsed reMarkable page."""

    TYPED = auto()  # Direct text extraction — no OCR needed
    HANDWRITING = auto()  # Render to PNG → vision LLM OCR
    BLANK = auto()  # No content — skip this page


def detect_page_type(rm_path: Path) -> PageType:
    """Detect the content type of a .rm file.

    Args:
        rm_path: Path to the .rm binary file.

    Returns:
        PageType enum value indicating how to process this page.
    """
    raise NotImplementedError("Milestone 2: implement page type detection")
