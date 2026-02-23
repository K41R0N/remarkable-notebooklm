"""Resolve human-readable notebook/folder names to reMarkable UUIDs."""

from __future__ import annotations

from dataclasses import dataclass

from rm_notebooklm.mapping.models import MappingEntry
from rm_notebooklm.remarkable.client import RemarkableClient
from rm_notebooklm.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class ResolvedMapping:
    """A MappingEntry with all names resolved to reMarkable UUIDs."""

    entry: MappingEntry
    rm_folder_id: str
    rm_document_id: str
    rm_responses_folder_id: str | None  # None if responses/ subfolder not yet created


def resolve_mapping_uuids(
    entry: MappingEntry,
    client: RemarkableClient,
) -> ResolvedMapping:
    """Resolve folder + notebook names to reMarkable UUIDs.

    Args:
        entry: Validated mapping entry with human-readable names.
        client: Authenticated reMarkable API client.

    Returns:
        ResolvedMapping with UUIDs populated.

    Raises:
        ValueError: If the folder or notebook name is not found in the cloud.
    """
    folders = client.list_folders()

    folder = next(
        (f for f in folders if f.vissible_name == entry.rm_folder),
        None,
    )
    if folder is None:
        raise ValueError(
            f"reMarkable folder not found: {entry.rm_folder!r}. "
            f"Available folders: {[f.vissible_name for f in folders]}"
        )

    docs = client.list_documents()
    notebook = next(
        (d for d in docs if d.vissible_name == entry.rm_notebook and d.parent == folder.id),
        None,
    )
    if notebook is None:
        raise ValueError(
            f"Notebook {entry.rm_notebook!r} not found in folder {entry.rm_folder!r}. "
            f"Available notebooks: {[d.vissible_name for d in docs if d.parent == folder.id]}"
        )

    responses_folder = next(
        (f for f in folders if f.vissible_name == entry.responses_folder and f.parent == folder.id),
        None,
    )

    log.info(
        "resolve_mapping_uuids",
        rm_folder=entry.rm_folder,
        rm_notebook=entry.rm_notebook,
        folder_id=folder.id,
        document_id=notebook.id,
        responses_folder_id=responses_folder.id if responses_folder else None,
    )

    return ResolvedMapping(
        entry=entry,
        rm_folder_id=folder.id,
        rm_document_id=notebook.id,
        rm_responses_folder_id=responses_folder.id if responses_folder else None,
    )
