"""Google Drive intermediary layer for NotebookLM source upload.

Used by both Path A and Path B to upload OCR'd text as Google Docs,
then reference them as NotebookLM sources via documentId.

OAuth scope: https://www.googleapis.com/auth/drive.file
(non-sensitive — only accesses files created by this app)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DriveDocument:
    """A Google Drive file created by this app."""

    file_id: str
    name: str
    web_view_link: str


class GoogleDriveClient:
    """Thin wrapper around google-api-python-client Drive v3."""

    def upload_text_as_doc(self, content: str, name: str) -> DriveDocument:
        """Upload a text string as a Google Doc.

        The returned file_id can be used directly in NotebookLM Enterprise's
        sources:batchCreate call as the documentId.

        Args:
            content: Plain text content to upload.
            name: Document display name.

        Returns:
            DriveDocument with file_id for use as NotebookLM source.
        """
        raise NotImplementedError("Milestone 4B: implement Google Drive upload")

    def delete_file(self, file_id: str) -> None:
        """Delete a file by ID (cleanup after NotebookLM has ingested it).

        Args:
            file_id: Google Drive file ID to delete.
        """
        raise NotImplementedError("Milestone 4B: implement delete_file")
