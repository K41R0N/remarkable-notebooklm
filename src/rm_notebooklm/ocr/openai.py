"""OpenAI GPT-4o / GPT-4o-mini OCR provider."""

from __future__ import annotations

from rm_notebooklm.ocr.base import OCRProvider


class OpenAIOCRProvider(OCRProvider):
    """OCR via OpenAI GPT-4o or GPT-4o-mini."""

    def transcribe(self, image: bytes) -> str:
        """Transcribe handwriting using GPT-4o.

        Args:
            image: Raw PNG bytes (preprocessed, ≤1568px long edge).

        Returns:
            Transcribed text.
        """
        raise NotImplementedError("Milestone 3: implement OpenAI OCR")
