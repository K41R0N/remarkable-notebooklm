"""Abstract OCR provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class OCRProvider(ABC):
    """Base class for all vision LLM OCR providers.

    All providers accept raw PNG bytes and return transcribed text.
    Swap providers by changing the OCR_PROVIDER env var — no pipeline
    code changes required.
    """

    #: System prompt injected before every OCR call.
    SYSTEM_PROMPT = "You are the world's greatest transcriber of handwritten notes."

    #: User prompt template for OCR requests.
    USER_PROMPT = (
        "Transcribe the handwritten text from this image accurately. "
        "This is from a digital e-ink tablet (black ink on white background).\n\n"
        "Rules:\n"
        "- Transcribe EXACTLY what is written — do not add, remove, or correct words\n"
        "- Preserve paragraph breaks, bullet points, numbered lists, and indentation\n"
        "- For mathematical notation, use LaTeX: inline $...$ and display $$...$$\n"
        "- For diagrams, arrows, or drawings, describe in [brackets]\n"
        "- If a word is ambiguous, use context to make your best guess\n"
        "- Output ONLY the transcribed text, no commentary"
    )

    @abstractmethod
    def transcribe(self, image: bytes) -> str:
        """Transcribe handwriting in a PNG image to text.

        Args:
            image: Raw PNG bytes of a preprocessed reMarkable page.

        Returns:
            Transcribed text string. Empty string for blank/illegible pages.

        Raises:
            OCRError: On API failure after all retries are exhausted.
        """
        raise NotImplementedError


class OCRError(Exception):
    """Raised when an OCR provider fails after all retries."""
