"""Shared pytest fixtures and VCR configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths to test fixture files
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"
RM_FILES_DIR = FIXTURES_DIR / "rm_files"
EXPECTED_TEXT_DIR = FIXTURES_DIR / "expected_text"
CASSETTES_DIR = FIXTURES_DIR / "cassettes"


# ---------------------------------------------------------------------------
# VCR configuration
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def vcr_config() -> dict:
    """Configure VCR cassette storage location and request matching."""
    return {
        "cassette_library_dir": str(CASSETTES_DIR),
        "record_mode": "none",  # Fail if cassette missing — no live calls in CI
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "filter_headers": [
            "Authorization",  # Hide JWT tokens
            "X-Goog-AuthUser",
        ],
        "filter_query_parameters": [
            "access_token",
        ],
    }


# ---------------------------------------------------------------------------
# Sample .rm file fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def typed_rm_file() -> Path:
    """Path to a .rm file containing only typed text (no handwriting)."""
    path = RM_FILES_DIR / "typed_text.rm"
    if not path.exists():
        pytest.skip(f"Fixture not found: {path}. Add sample .rm files from rmscene test suite.")
    return path


@pytest.fixture
def handwriting_rm_file() -> Path:
    """Path to a .rm file containing handwriting strokes."""
    path = RM_FILES_DIR / "handwriting.rm"
    if not path.exists():
        pytest.skip(f"Fixture not found: {path}. Add sample .rm files from rmscene test suite.")
    return path


@pytest.fixture
def blank_rm_file() -> Path:
    """Path to a .rm file with no content (blank page)."""
    path = RM_FILES_DIR / "blank.rm"
    if not path.exists():
        pytest.skip(f"Fixture not found: {path}. Add sample .rm files from rmscene test suite.")
    return path


# ---------------------------------------------------------------------------
# State DB fixture (in-memory)
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_state_db(tmp_path: Path):
    """StateDB instance backed by a temporary SQLite file."""
    from rm_notebooklm.state.db import StateDB

    return StateDB(tmp_path / "test_state.db")
