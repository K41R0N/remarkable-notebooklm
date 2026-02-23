"""SQLite state tracking for processed pages.

Schema (processed_pages):
  page_id            TEXT  PRIMARY KEY  — reMarkable page UUID
  notebook_id        TEXT  NOT NULL     — parent notebook UUID
  content_hash       TEXT  NOT NULL     — SHA-256 of .rm file bytes
  ocr_text           TEXT               — extracted/transcribed text
  notebooklm_nb_id   TEXT               — NotebookLM/GCS notebook/bucket ID
  pdf_uploaded       BOOL  DEFAULT 0    — True after response PDF uploaded
  processed_at       TEXT  NOT NULL     — ISO-8601 timestamp
  version            INT   NOT NULL     — reMarkable document version at time of processing
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS processed_pages (
    page_id             TEXT PRIMARY KEY,
    notebook_id         TEXT NOT NULL,
    content_hash        TEXT NOT NULL,
    ocr_text            TEXT,
    notebooklm_nb_id    TEXT,
    pdf_uploaded        BOOLEAN NOT NULL DEFAULT 0,
    processed_at        TEXT NOT NULL,
    version             INTEGER NOT NULL
);
"""


class StateDB:
    """SQLite-backed state store for idempotent pipeline execution."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(CREATE_TABLE_SQL)

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def is_processed(self, page_id: str, content_hash: str) -> bool:
        """Return True if this exact page version has already been processed.

        Args:
            page_id: reMarkable page UUID.
            content_hash: SHA-256 hash of the current .rm file bytes.

        Returns:
            True if a row exists with matching page_id AND content_hash.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM processed_pages WHERE page_id = ? AND content_hash = ?",
                (page_id, content_hash),
            ).fetchone()
        return row is not None

    def mark_processed(
        self,
        *,
        page_id: str,
        notebook_id: str,
        content_hash: str,
        ocr_text: str | None = None,
        version: int,
    ) -> None:
        """Insert or update a processed page record.

        Args:
            page_id: reMarkable page UUID.
            notebook_id: Parent notebook UUID.
            content_hash: SHA-256 of .rm file bytes.
            ocr_text: Extracted or OCR'd text (None if not yet processed).
            version: reMarkable document version number.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO processed_pages
                   (page_id, notebook_id, content_hash, ocr_text, processed_at, version)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(page_id) DO UPDATE SET
                     content_hash=excluded.content_hash,
                     ocr_text=excluded.ocr_text,
                     processed_at=excluded.processed_at,
                     version=excluded.version
                """,
                (page_id, notebook_id, content_hash, ocr_text, now, version),
            )

    def mark_pdf_uploaded(self, page_id: str) -> None:
        """Set pdf_uploaded=True for a page after upload succeeds."""
        raise NotImplementedError("Milestone 5: implement mark_pdf_uploaded")
