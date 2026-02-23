"""Tests for reMarkable authentication and token refresh logic."""

from __future__ import annotations

import responses as mock_responses

from rm_notebooklm.remarkable.auth import (
    USER_TOKEN_URL,
    AuthenticationError,
    auto_refresh_token,
)
from rm_notebooklm.remarkable.client import RemarkableClient

DOCS_URL = "https://document-storage-production-dot-remarkable-production.appspot.com/document-storage/json/2/docs"


class TestAutoRefreshToken:
    """Test the auto_refresh_token decorator."""

    def test_no_refresh_on_success(self) -> None:
        """Decorator does not call _refresh_user_token if request succeeds."""
        refresh_called = []

        class FakeClient:
            def _refresh_user_token(self) -> None:
                refresh_called.append(True)

            @auto_refresh_token(max_retries=1)
            def do_something(self) -> str:
                return "ok"

        client = FakeClient()
        result = client.do_something()
        assert result == "ok"
        assert len(refresh_called) == 0

    def test_refresh_on_auth_error(self) -> None:
        """Decorator calls _refresh_user_token once after AuthenticationError."""
        call_count = [0]
        refresh_called = [0]

        class FakeClient:
            def _refresh_user_token(self) -> None:
                refresh_called[0] += 1

            @auto_refresh_token(max_retries=1)
            def do_something(self) -> str:
                call_count[0] += 1
                if call_count[0] == 1:
                    raise AuthenticationError("Token expired")
                return "ok after refresh"

        client = FakeClient()
        result = client.do_something()
        assert result == "ok after refresh"
        assert refresh_called[0] == 1
        assert call_count[0] == 2

    def test_reraises_after_max_retries(self) -> None:
        """Decorator re-raises AuthenticationError after max_retries exhausted."""

        class FakeClient:
            def _refresh_user_token(self) -> None:
                pass

            @auto_refresh_token(max_retries=1)
            def do_something(self) -> str:
                raise AuthenticationError("Always fails")

        import pytest

        client = FakeClient()
        with pytest.raises(AuthenticationError):
            client.do_something()


class TestRemarkableClientTokenRefresh:
    """Integration-style tests for RemarkableClient token refresh via responses mock."""

    @mock_responses.activate
    def test_token_refresh_on_401(self) -> None:
        """list_documents() retries with new token after 401 response."""
        mock_responses.add(mock_responses.GET, DOCS_URL, status=401, body="Token is expired")
        mock_responses.add(mock_responses.POST, USER_TOKEN_URL, body="new-jwt-token", status=200)
        mock_responses.add(
            mock_responses.GET,
            DOCS_URL,
            json=[
                {
                    "ID": "test-uuid",
                    "VissibleName": "My Notes",
                    "Version": 1,
                    "BlobURLGet": "https://storage.googleapis.com/fake",
                    "Type": "DocumentType",
                    "Parent": "",
                    "Bookmarked": False,
                    "Tags": [],
                }
            ],
            status=200,
        )

        client = RemarkableClient(device_token="dev-tok", user_token="expired-tok")
        docs = client.list_documents()
        assert len(docs) == 1
        assert docs[0].vissible_name == "My Notes"
        assert len(mock_responses.calls) == 3
