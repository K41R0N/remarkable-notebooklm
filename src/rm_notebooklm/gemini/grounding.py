"""Gemini API with document grounding (Path C — default for production).

This is the recommended path: fully official API, no cookie fragility,
no Enterprise contract required. Uses google-generativeai SDK with
Google Cloud Storage for document storage.

Approach:
  1. Upload OCR'd text to GCS bucket
  2. Call Gemini API with file URI as grounded document
  3. Receive AI response grounded in the uploaded content

Reuses GEMINI_API_KEY — no additional credentials needed beyond GCS bucket.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AIResponse:
    """Structured AI response from Gemini grounded query."""

    text: str
    source_ids: list[str] = field(default_factory=list)
    notebook_id: str | None = None
    model: str = "gemini-2.5-flash"


class GeminiGroundingClient:
    """Gemini API client with GCS-backed document grounding (Path C)."""

    def upload_source(self, content: str, name: str) -> str:
        """Upload text to GCS and return the GCS URI.

        Args:
            content: OCR'd text from a reMarkable page.
            name: Document identifier (used as GCS object name).

        Returns:
            GCS URI (gs://bucket/object) for use in grounded queries.
        """
        raise NotImplementedError("Milestone 4A: implement GCS upload")

    def query(self, source_uri: str, prompt: str) -> AIResponse:
        """Query Gemini with a document grounding source.

        Args:
            source_uri: GCS URI from upload_source().
            prompt: Question or instruction for the AI.

        Returns:
            AIResponse with grounded text and metadata.
        """
        raise NotImplementedError("Milestone 4A: implement Gemini grounded query")
