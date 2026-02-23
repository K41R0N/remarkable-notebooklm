"""End-to-end pipeline tests.

Requires real credentials and a connected reMarkable device.
Run with: pytest tests/e2e/ -v -m e2e --run-e2e

These tests:
  1. Upload a known test document to reMarkable
  2. Run the full pipeline (sync → parse → OCR → query → PDF → upload)
  3. Assert the response PDF appears in the document list
  4. Clean up test documents

NEVER run these in CI. They write to real services.
"""

from __future__ import annotations

import pytest


def pytest_addoption(parser) -> None:
    parser.addoption("--run-e2e", action="store_true", default=False, help="Run E2E tests")


def pytest_collection_modifyitems(config, items) -> None:
    if not config.getoption("--run-e2e"):
        skip_e2e = pytest.mark.skip(reason="Pass --run-e2e to run E2E tests")
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip_e2e)


@pytest.mark.e2e
def test_full_pipeline_round_trip() -> None:
    """Full pipeline: reMarkable → OCR → Gemini → PDF → reMarkable."""
    pytest.skip("Milestone 6: implement full pipeline first")
