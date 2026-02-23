"""Notebook-to-NotebookLM mapping configuration."""

from rm_notebooklm.mapping.loader import load_mappings
from rm_notebooklm.mapping.models import MappingEntry, MappingsConfig
from rm_notebooklm.mapping.resolver import ResolvedMapping, resolve_mapping_uuids

__all__ = [
    "MappingEntry",
    "MappingsConfig",
    "ResolvedMapping",
    "load_mappings",
    "resolve_mapping_uuids",
]
