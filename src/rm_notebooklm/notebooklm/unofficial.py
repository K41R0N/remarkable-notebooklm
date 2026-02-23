"""Unofficial notebooklm-py client (Path A).

WARNING: This path uses cookie-based authentication against the consumer
NotebookLM web app. Cookies expire every 1-2 weeks and require re-auth
via Playwright browser. Use Path C (Gemini grounding) for production.

Library: notebooklm-py v0.3.0 (install with [browser] extra)
  pip install "notebooklm-py[browser]==0.3.0"

To authenticate:
  notebooklm login
  (Opens Playwright Chromium, complete Google login)
  (Session saved to ~/.notebooklm/storage_state.json)
"""

from __future__ import annotations

from dataclasses import dataclass


class CookieExpiredError(Exception):
    """Raised when notebooklm-py detects expired session cookies.

    Run `notebooklm login` to re-authenticate.
    """


@dataclass
class ChatResponse:
    """Response from a NotebookLM grounded chat query."""

    answer: str
    notebook_id: str
    source_ids: list[str]


class NotebookLMUnofficialClient:
    """Cookie-based NotebookLM client via notebooklm-py (Path A — fragile)."""

    async def ask(self, notebook_id: str, question: str) -> ChatResponse:
        """Query a notebook with a grounded question.

        Args:
            notebook_id: NotebookLM notebook ID.
            question: Question to ask against the notebook's sources.

        Returns:
            ChatResponse with grounded answer and source citations.

        Raises:
            CookieExpiredError: If session cookies have expired.
        """
        raise NotImplementedError("Milestone 4C: implement unofficial chat")
