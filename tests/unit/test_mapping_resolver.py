"""Tests for mapping UUID resolver."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rm_notebooklm.mapping.models import MappingEntry
from rm_notebooklm.mapping.resolver import ResolvedMapping, resolve_mapping_uuids
from rm_notebooklm.remarkable.client import RemarkableDocument


def _make_folder(
    id: str,
    vissible_name: str,
    parent: str = "",
) -> RemarkableDocument:
    """Build a RemarkableDocument representing a folder (CollectionType)."""
    return RemarkableDocument(
        id=id,
        vissible_name=vissible_name,
        version=1,
        blob_url_get="",
        parent=parent,
        type="CollectionType",
    )


def _make_document(
    id: str,
    vissible_name: str,
    parent: str = "",
) -> RemarkableDocument:
    """Build a RemarkableDocument representing a notebook (DocumentType)."""
    return RemarkableDocument(
        id=id,
        vissible_name=vissible_name,
        version=1,
        blob_url_get="",
        parent=parent,
        type="DocumentType",
    )


def _make_entry(
    rm_folder: str = "Work",
    rm_notebook: str = "Meeting Notes",
    notebooklm_nb_id: str = "nb-abc",
    responses_folder: str = "responses",
) -> MappingEntry:
    return MappingEntry(
        rm_folder=rm_folder,
        rm_notebook=rm_notebook,
        notebooklm_nb_id=notebooklm_nb_id,
        responses_folder=responses_folder,
    )


class TestResolveMappingUuids:
    """Tests for resolve_mapping_uuids()."""

    def test_resolves_folder_and_notebook(self) -> None:
        """Happy path: folder and notebook found, ResolvedMapping returned with correct IDs."""
        folder = _make_folder("folder-uuid-1", "Work")
        notebook = _make_document("doc-uuid-1", "Meeting Notes", parent="folder-uuid-1")

        client = MagicMock()
        client.list_folders.return_value = [folder]
        client.list_documents.return_value = [notebook]

        entry = _make_entry(rm_folder="Work", rm_notebook="Meeting Notes")
        result = resolve_mapping_uuids(entry, client)

        assert isinstance(result, ResolvedMapping)
        assert result.rm_folder_id == "folder-uuid-1"
        assert result.rm_document_id == "doc-uuid-1"
        assert result.entry is entry

    def test_responses_folder_found(self) -> None:
        """When a responses subfolder exists, rm_responses_folder_id is set."""
        folder = _make_folder("folder-uuid-1", "Work")
        notebook = _make_document("doc-uuid-1", "Meeting Notes", parent="folder-uuid-1")
        responses = _make_folder("resp-uuid-1", "responses", parent="folder-uuid-1")

        client = MagicMock()
        client.list_folders.return_value = [folder, responses]
        client.list_documents.return_value = [notebook]

        entry = _make_entry(rm_folder="Work", rm_notebook="Meeting Notes")
        result = resolve_mapping_uuids(entry, client)

        assert result.rm_responses_folder_id == "resp-uuid-1"

    def test_responses_folder_missing(self) -> None:
        """When no responses subfolder exists, rm_responses_folder_id is None."""
        folder = _make_folder("folder-uuid-1", "Work")
        notebook = _make_document("doc-uuid-1", "Meeting Notes", parent="folder-uuid-1")

        client = MagicMock()
        client.list_folders.return_value = [folder]
        client.list_documents.return_value = [notebook]

        entry = _make_entry(rm_folder="Work", rm_notebook="Meeting Notes")
        result = resolve_mapping_uuids(entry, client)

        assert result.rm_responses_folder_id is None

    def test_folder_not_found_raises_value_error(self) -> None:
        """ValueError is raised (with folder name in message) when folder not found."""
        other_folder = _make_folder("other-uuid", "Other")

        client = MagicMock()
        client.list_folders.return_value = [other_folder]
        client.list_documents.return_value = []

        entry = _make_entry(rm_folder="Work")

        with pytest.raises(ValueError, match="Work"):
            resolve_mapping_uuids(entry, client)

    def test_notebook_not_found_raises_value_error(self) -> None:
        """ValueError is raised (with notebook name in message) when notebook not in folder."""
        folder = _make_folder("folder-uuid-1", "Work")
        other_doc = _make_document("doc-uuid-2", "Other Notes", parent="folder-uuid-1")

        client = MagicMock()
        client.list_folders.return_value = [folder]
        client.list_documents.return_value = [other_doc]

        entry = _make_entry(rm_folder="Work", rm_notebook="Meeting Notes")

        with pytest.raises(ValueError, match="Meeting Notes"):
            resolve_mapping_uuids(entry, client)

    def test_notebook_parent_checked(self) -> None:
        """A notebook with the correct name but wrong parent folder is not matched."""
        folder = _make_folder("folder-uuid-1", "Work")
        # Same name, but under a different parent
        notebook_wrong_parent = _make_document(
            "doc-uuid-3", "Meeting Notes", parent="other-folder-uuid"
        )

        client = MagicMock()
        client.list_folders.return_value = [folder]
        client.list_documents.return_value = [notebook_wrong_parent]

        entry = _make_entry(rm_folder="Work", rm_notebook="Meeting Notes")

        with pytest.raises(ValueError, match="Meeting Notes"):
            resolve_mapping_uuids(entry, client)
