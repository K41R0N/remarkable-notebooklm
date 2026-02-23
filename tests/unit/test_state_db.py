"""Tests for SQLite state tracking."""

from __future__ import annotations

from pathlib import Path

import pytest

from rm_notebooklm.state.db import StateDB


class TestStateDB:
    """Test StateDB CRUD operations and deduplication logic."""

    def test_is_processed_returns_false_for_new_page(self, tmp_state_db: StateDB) -> None:
        """is_processed() returns False for a page that hasn't been processed."""
        assert tmp_state_db.is_processed("new-page-id", "abc123hash") is False

    def test_mark_processed_and_check(self, tmp_state_db: StateDB) -> None:
        """After mark_processed(), is_processed() returns True for same hash."""
        tmp_state_db.mark_processed(
            page_id="page-uuid-1",
            notebook_id="notebook-uuid-1",
            content_hash="sha256hashvalue",
            ocr_text="Hello world",
            version=5,
        )
        assert tmp_state_db.is_processed("page-uuid-1", "sha256hashvalue") is True

    def test_different_hash_not_processed(self, tmp_state_db: StateDB) -> None:
        """is_processed() returns False when content_hash differs (page changed)."""
        tmp_state_db.mark_processed(
            page_id="page-uuid-1",
            notebook_id="notebook-uuid-1",
            content_hash="old-hash",
            version=1,
        )
        assert tmp_state_db.is_processed("page-uuid-1", "new-hash") is False

    def test_mark_pdf_uploaded(self, tmp_state_db: StateDB) -> None:
        """mark_pdf_uploaded() sets pdf_uploaded=True for a processed page."""
        pytest.skip("Milestone 5: implement mark_pdf_uploaded first")

    def test_db_init_is_idempotent(self, tmp_path: Path) -> None:
        """Constructing StateDB twice on the same path doesn't raise."""
        db_path = tmp_path / "state.db"
        StateDB(db_path)
        StateDB(db_path)  # Should not raise

    def test_mark_processed_stores_notebooklm_nb_id(self, tmp_state_db: StateDB) -> None:
        """mark_processed() with notebooklm_nb_id stores the value in the row."""
        import sqlite3

        tmp_state_db.mark_processed(
            page_id="page-nb-1",
            notebook_id="notebook-uuid-1",
            content_hash="hashvalue",
            version=1,
            notebooklm_nb_id="nb123",
        )
        conn = sqlite3.connect(tmp_state_db._db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT notebooklm_nb_id FROM processed_pages WHERE page_id = ?",
            ("page-nb-1",),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["notebooklm_nb_id"] == "nb123"

    def test_mark_processed_notebooklm_nb_id_default_none(self, tmp_state_db: StateDB) -> None:
        """mark_processed() without notebooklm_nb_id stores NULL in the row."""
        import sqlite3

        tmp_state_db.mark_processed(
            page_id="page-nb-2",
            notebook_id="notebook-uuid-2",
            content_hash="hashvalue2",
            version=1,
        )
        conn = sqlite3.connect(tmp_state_db._db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT notebooklm_nb_id FROM processed_pages WHERE page_id = ?",
            ("page-nb-2",),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["notebooklm_nb_id"] is None

    def test_mark_processed_updates_notebooklm_nb_id_on_conflict(
        self, tmp_state_db: StateDB
    ) -> None:
        """Re-inserting with a new notebooklm_nb_id updates the existing row."""
        import sqlite3

        # First insert with None
        tmp_state_db.mark_processed(
            page_id="page-nb-3",
            notebook_id="notebook-uuid-3",
            content_hash="hashvalue3",
            version=1,
            notebooklm_nb_id=None,
        )
        # Second insert (conflict) with an actual nb_id
        tmp_state_db.mark_processed(
            page_id="page-nb-3",
            notebook_id="notebook-uuid-3",
            content_hash="hashvalue3",
            version=2,
            notebooklm_nb_id="nb-updated",
        )
        conn = sqlite3.connect(tmp_state_db._db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT notebooklm_nb_id FROM processed_pages WHERE page_id = ?",
            ("page-nb-3",),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["notebooklm_nb_id"] == "nb-updated"
