"""Integration tests for reMarkable Cloud API — uses responses mock.

These tests verify the full request/response cycle without live network calls.
To record real VCR cassettes once credentials are available:
    pytest tests/integration/ --vcr-record=all
Then commit cassettes to tests/fixtures/cassettes/ and CI will use them
with --vcr-record=none (already configured in pyproject.toml).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import responses as mock_responses

from rm_notebooklm.remarkable.auth import USER_TOKEN_URL
from rm_notebooklm.remarkable.client import LIST_URL, RemarkableClient

FAKE_DOCS = [
    {
        "ID": "doc-uuid-1",
        "VissibleName": "My Notes",
        "Version": 3,
        "BlobURLGet": "https://storage.googleapis.com/rm-bucket/doc-uuid-1.zip",
        "Type": "DocumentType",
        "Parent": "",
        "Bookmarked": False,
        "Tags": [],
    },
    {
        "ID": "doc-uuid-2",
        "VissibleName": "Quick Sketch",
        "Version": 1,
        "BlobURLGet": "https://storage.googleapis.com/rm-bucket/doc-uuid-2.zip",
        "Type": "DocumentType",
        "Parent": "",
        "Bookmarked": True,
        "Tags": [],
    },
    {
        "ID": "folder-uuid-1",
        "VissibleName": "Archive",
        "Version": 2,
        "BlobURLGet": "",
        "Type": "CollectionType",
        "Parent": "",
        "Bookmarked": False,
        "Tags": [],
    },
]


@mock_responses.activate
def test_list_documents_returns_docs() -> None:
    """list_documents() returns parsed document objects, filtering out collections."""
    mock_responses.add(mock_responses.GET, LIST_URL, json=FAKE_DOCS, status=200)

    client = RemarkableClient(device_token="dev-tok", user_token="user-tok")
    docs = client.list_documents()

    assert len(docs) == 2  # CollectionType filtered out
    assert docs[0].id == "doc-uuid-1"
    assert docs[0].vissible_name == "My Notes"
    assert docs[0].version == 3
    assert docs[1].bookmarked is True


@mock_responses.activate
def test_list_documents_refreshes_token_on_401() -> None:
    """list_documents() automatically refreshes token on 401 and retries."""
    mock_responses.add(mock_responses.GET, LIST_URL, status=401, body="Token expired")
    mock_responses.add(mock_responses.POST, USER_TOKEN_URL, body="fresh-token", status=200)
    mock_responses.add(mock_responses.GET, LIST_URL, json=[FAKE_DOCS[0]], status=200)

    client = RemarkableClient(device_token="dev-tok", user_token="expired-tok")
    docs = client.list_documents()

    assert len(docs) == 1
    assert docs[0].vissible_name == "My Notes"
    assert len(mock_responses.calls) == 3
    # Third call should use the new token
    assert "fresh-token" in mock_responses.calls[2].request.headers["Authorization"]


@mock_responses.activate
def test_download_zip_saves_file(tmp_path: Path) -> None:
    """download_zip() saves ZIP to dest_dir and returns the path."""
    fake_zip_content = b"PK\x03\x04fake-zip-content"
    blob_url = "https://storage.googleapis.com/rm-bucket/doc-uuid-1.zip"

    mock_responses.add(mock_responses.GET, LIST_URL, json=[FAKE_DOCS[0]], status=200)
    mock_responses.add(mock_responses.GET, blob_url, body=fake_zip_content, status=200)

    client = RemarkableClient(device_token="dev-tok", user_token="user-tok")
    docs = client.list_documents()

    dest = tmp_path / "downloads"
    zip_path = client.download_zip(docs[0], dest)

    assert zip_path.exists()
    assert zip_path.name == "doc-uuid-1.zip"
    assert zip_path.read_bytes() == fake_zip_content


@mock_responses.activate
def test_download_zip_no_auth_header() -> None:
    """download_zip() does NOT send Authorization header (signed GCS URL)."""
    from rm_notebooklm.remarkable.client import RemarkableDocument

    blob_url = "https://storage.googleapis.com/rm-bucket/doc-uuid-1.zip"
    mock_responses.add(mock_responses.GET, blob_url, body=b"fake", status=200)

    client = RemarkableClient(device_token="dev-tok", user_token="user-tok")
    doc = RemarkableDocument(
        id="doc-uuid-1",
        vissible_name="My Notes",
        version=3,
        blob_url_get=blob_url,
    )

    with tempfile.TemporaryDirectory() as d:
        client.download_zip(doc, Path(d))

    download_call = mock_responses.calls[0]
    assert "Authorization" not in download_call.request.headers


@pytest.mark.vcr  # type: ignore[misc]
def test_upload_pdf_returns_uuid(tmp_path: Path) -> None:
    """upload_pdf() completes 3-step upload and returns new document UUID."""
    pytest.skip("Milestone 5: record VCR cassette and implement upload_pdf")
