"""Incremental sync — download only new/changed documents.

Dedup strategy (M1): filesystem-level — skip documents whose ZIP already
exists in download_dir. The processed_pages SQLite table is page-scoped;
pages don't exist as separate entities until Milestone 2 parses ZIPs.
M2 will call state_db.mark_processed() per extracted page.
"""

from __future__ import annotations

from pathlib import Path

from rm_notebooklm.remarkable.client import RemarkableClient
from rm_notebooklm.utils.logging import get_logger


class SyncManager:
    """Orchestrates incremental reMarkable → local sync."""

    def __init__(self, client: RemarkableClient, download_dir: Path) -> None:
        self._client = client
        self._download_dir = download_dir
        self._log = get_logger(__name__)

    def sync(self, dry_run: bool = False) -> list[Path]:
        """Download all new or changed documents.

        Skips documents whose ZIP already exists in download_dir (filesystem dedup).

        Args:
            dry_run: If True, log what would be downloaded without downloading.

        Returns:
            List of paths to newly downloaded ZIP files (empty in dry_run).
        """
        docs = self._client.list_documents()
        downloaded: list[Path] = []

        for doc in docs:
            zip_path = self._download_dir / f"{doc.id}.zip"
            if zip_path.exists():
                self._log.debug(
                    "skipping_existing",
                    doc_id=doc.id,
                    name=doc.vissible_name,
                    version=doc.version,
                )
                continue
            if dry_run:
                self._log.info(
                    "would_download",
                    doc_id=doc.id,
                    name=doc.vissible_name,
                    version=doc.version,
                )
                continue
            self._log.info(
                "downloading",
                doc_id=doc.id,
                name=doc.vissible_name,
                version=doc.version,
            )
            zip_path = self._client.download_zip(doc, self._download_dir)
            downloaded.append(zip_path)

        return downloaded
