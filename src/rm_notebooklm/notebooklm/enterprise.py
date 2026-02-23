"""NotebookLM Enterprise API client (Path B).

Base URL: https://{ENDPOINT_LOCATION}-discoveryengine.googleapis.com/v1alpha/
          projects/{PROJECT_NUMBER}/locations/{LOCATION}/notebooks

IMPORTANT: The v1alpha API has NO chat/query endpoint. Use this path for
source management only. Route AI queries through Path C (Gemini grounding).

Required IAM roles:
  - Cloud NotebookLM Admin
  - Cloud NotebookLM User

Required API:
  - Discovery Engine API (discoveryengine.googleapis.com)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NotebookLMSource:
    """A source document added to a NotebookLM notebook."""

    source_id: str
    notebook_id: str
    document_name: str


class NotebookLMEnterpriseClient:
    """Client for NotebookLM Enterprise REST API (Path B)."""

    def create_notebook(self, name: str) -> str:
        """Create a new notebook.

        Args:
            name: Display name for the notebook.

        Returns:
            Notebook resource ID.
        """
        raise NotImplementedError("Milestone 4B: implement create_notebook")

    def add_source_file(self, notebook_id: str, content: bytes, filename: str) -> NotebookLMSource:
        """Upload a file directly as a notebook source.

        Supports: PDF, TXT, MD, DOCX, PPTX, XLSX, audio, images (≤200MB).

        Args:
            notebook_id: Target notebook resource ID.
            content: File bytes.
            filename: Filename with extension for MIME type detection.

        Returns:
            NotebookLMSource with assigned source_id.
        """
        raise NotImplementedError("Milestone 4B: implement add_source_file")

    def add_source_from_drive(self, notebook_id: str, document_id: str) -> NotebookLMSource:
        """Add a Google Drive document as a notebook source.

        Args:
            notebook_id: Target notebook resource ID.
            document_id: Google Drive file ID (from Drive API response).

        Returns:
            NotebookLMSource with assigned source_id.
        """
        raise NotImplementedError("Milestone 4B: implement add_source_from_drive")
