"""Pydantic models for notebook-to-NotebookLM mapping configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class MappingEntry(BaseModel):
    """A single reMarkable notebook → NotebookLM project mapping."""

    rm_folder: str
    rm_notebook: str
    notebooklm_nb_id: str
    responses_folder: str = "responses"
    notebooklm_path: Literal["A", "B", "C"] | None = None


class MappingsConfig(BaseModel):
    """Top-level structure of mappings.yaml."""

    mappings: list[MappingEntry]
