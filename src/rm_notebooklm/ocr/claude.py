"""Claude Sonnet/Haiku OCR provider.

Note: Claude auto-resizes images where the long edge exceeds 1568px.
The preprocessor MUST resize to ≤1568px before calling this provider.
"""

from __future__ import annotations

from rm_notebooklm.ocr.base import OCRProvider


class ClaudeOCRProvider(OCRProvider):
    """OCR via Anthropic Claude Sonnet or Haiku."""

    #: reMarkable height (1872px) exceeds Claude's 1568px threshold.
    #: Preprocessor handles resize; this is a guard for direct callers.
    MAX_LONG_EDGE = 1568

    def transcribe(self, image: bytes) -> str:
        """Transcribe handwriting using Claude.

        Args:
            image: Raw PNG bytes. Long edge MUST be ≤1568px.

        Returns:
            Transcribed text.
        """
        raise NotImplementedError("Milestone 3: implement Claude OCR")
