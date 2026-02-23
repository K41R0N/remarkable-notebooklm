"""RemarkableClient — list, download, and upload documents.

API base: https://document-storage-production-dot-remarkable-production.appspot.com

Key API quirk: field is 'VissibleName' (typo in the real API — not a mistake here).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import requests

from rm_notebooklm.remarkable.auth import AuthenticationError, auto_refresh_token
from rm_notebooklm.utils.retry import remarkable_breaker

STORAGE_BASE = "https://document-storage-production-dot-remarkable-production.appspot.com"
LIST_URL = f"{STORAGE_BASE}/document-storage/json/2/docs"
UPLOAD_REQUEST_URL = f"{STORAGE_BASE}/document-storage/json/2/upload/request"
UPLOAD_STATUS_URL = f"{STORAGE_BASE}/document-storage/json/2/upload/update-status"
DELETE_URL = f"{STORAGE_BASE}/document-storage/json/2/delete"


@dataclass
class RemarkableDocument:
    """Represents a document entry from the reMarkable Cloud API."""

    id: str
    vissible_name: str  # Intentional typo — matches 'VissibleName' in API
    version: int
    blob_url_get: str
    parent: str = ""
    type: str = "DocumentType"
    bookmarked: bool = False
    tags: list[str] = field(default_factory=list)


class RemarkableClient:
    """Client for reMarkable Cloud document storage API."""

    def __init__(self, device_token: str, user_token: str = "") -> None:
        self._device_token = device_token
        self._user_token = user_token

    def _refresh_user_token(self) -> None:
        """Refresh the short-lived user token using the device token."""
        from rm_notebooklm.remarkable.auth import refresh_user_token

        self._user_token = refresh_user_token(self._device_token)

    @auto_refresh_token(max_retries=1)
    def list_documents(self) -> list[RemarkableDocument]:
        """List all documents with blob download URLs.

        Returns:
            List of RemarkableDocument instances (DocumentType only).

        Raises:
            AuthenticationError: On 401 (auto-refreshes once then raises).
        """

        def _call() -> list[dict]:  # type: ignore[type-arg]
            resp = requests.get(
                LIST_URL,
                headers={"Authorization": f"Bearer {self._user_token}"},
                params={"withBlob": "true"},
                timeout=30,
            )
            if resp.status_code == 401:
                raise AuthenticationError("User token expired")
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

        items: list[dict] = remarkable_breaker.call(_call)  # type: ignore[type-arg]
        return [
            RemarkableDocument(
                id=item["ID"],
                vissible_name=item.get("VissibleName", ""),
                version=item.get("Version", 0),
                blob_url_get=item.get("BlobURLGet", ""),
                parent=item.get("Parent", ""),
                type=item.get("Type", "DocumentType"),
                bookmarked=item.get("Bookmarked", False),
                tags=item.get("Tags", []),
            )
            for item in items
            if item.get("Type") == "DocumentType"
        ]

    @auto_refresh_token(max_retries=1)
    def list_folders(self) -> list[RemarkableDocument]:
        """List all collection (folder) items.

        Returns:
            List of RemarkableDocument instances with type='CollectionType'.

        Raises:
            AuthenticationError: On 401 (auto-refreshes once then raises).
        """

        def _call() -> list[dict]:  # type: ignore[type-arg]
            resp = requests.get(
                LIST_URL,
                headers={"Authorization": f"Bearer {self._user_token}"},
                params={"withBlob": "true"},
                timeout=30,
            )
            if resp.status_code == 401:
                raise AuthenticationError("User token expired")
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

        items: list[dict] = remarkable_breaker.call(_call)  # type: ignore[type-arg]
        return [
            RemarkableDocument(
                id=item["ID"],
                vissible_name=item.get("VissibleName", ""),
                version=item.get("Version", 0),
                blob_url_get=item.get("BlobURLGet", ""),
                parent=item.get("Parent", ""),
                type=item.get("Type", "CollectionType"),
                bookmarked=item.get("Bookmarked", False),
                tags=item.get("Tags", []),
            )
            for item in items
            if item.get("Type") == "CollectionType"
        ]

    def download_zip(self, document: RemarkableDocument, dest_dir: Path) -> Path:
        """Download document ZIP archive to dest_dir.

        Args:
            document: Document with a valid BlobURLGet (signed GCS URL — no auth needed).
            dest_dir: Directory to save the ZIP.

        Returns:
            Path to the downloaded ZIP file.
        """
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"{document.id}.zip"

        def _call() -> None:
            resp = requests.get(document.blob_url_get, timeout=120, stream=True)
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)

        remarkable_breaker.call(_call)
        return dest_path

    def upload_pdf(self, pdf_path: Path, name: str, parent_id: str = "") -> str:
        """Upload a PDF as a new reMarkable document (3-step process).

        Steps:
            1. PUT /upload/request to get a BlobURLPut
            2. PUT <BlobURLPut> with the ZIP contents (no auth header)
            3. PUT /upload/update-status to finalize

        Args:
            pdf_path: Path to the PDF file.
            name: Document name (VissibleName in API).
            parent_id: Parent folder UUID (empty string = root).

        Returns:
            New document UUID.
        """
        raise NotImplementedError("Milestone 5: implement upload_pdf")
