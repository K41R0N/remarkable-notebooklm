"""Gemini 2.5 Flash OCR provider.

Default provider: ~$0.002/page, free tier available for development.
"""

from __future__ import annotations

from rm_notebooklm.ocr.base import OCRProvider


class GeminiOCRProvider(OCRProvider):
    """OCR via Google Gemini 2.5 Flash."""

    def transcribe(self, image: bytes) -> str:
        """Transcribe handwriting using Gemini 2.5 Flash.

        Args:
            image: Raw PNG bytes (preprocessed, ≤1568px long edge).

        Returns:
            Transcribed text.
        """
        raise NotImplementedError("Milestone 3: implement Gemini OCR")
