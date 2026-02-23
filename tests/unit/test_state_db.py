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
