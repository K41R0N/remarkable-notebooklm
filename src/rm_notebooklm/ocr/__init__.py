"""Vision LLM OCR providers."""

from __future__ import annotations

from rm_notebooklm.ocr.base import OCRProvider


def get_provider(provider_name: str) -> OCRProvider:
    """Return an OCRProvider instance by name.

    Args:
        provider_name: One of "gemini", "openai", "claude".

    Returns:
        Configured OCRProvider instance.

    Raises:
        ValueError: If provider_name is not recognized.
    """
    match provider_name.lower():
        case "gemini":
            from rm_notebooklm.ocr.gemini import GeminiOCRProvider

            return GeminiOCRProvider()
        case "openai":
            from rm_notebooklm.ocr.openai import OpenAIOCRProvider

            return OpenAIOCRProvider()
        case "claude":
            from rm_notebooklm.ocr.claude import ClaudeOCRProvider

            return ClaudeOCRProvider()
        case _:
            raise ValueError(
                f"Unknown OCR provider: {provider_name!r}. Choose: gemini, openai, claude"
            )


__all__ = ["OCRProvider", "get_provider"]
