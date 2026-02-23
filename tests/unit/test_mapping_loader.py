"""Tests for mapping YAML loader."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from rm_notebooklm.mapping.loader import load_mappings
from rm_notebooklm.mapping.models import MappingEntry


class TestLoadMappings:
    """Tests for load_mappings()."""

    def test_missing_file_returns_empty_list(self, tmp_path: Path) -> None:
        """load_mappings() returns [] when the file does not exist."""
        result = load_mappings(tmp_path / "nonexistent.yaml")
        assert result == []

    def test_valid_yaml_loads_entries(self, tmp_path: Path) -> None:
        """A valid YAML file with one entry returns a list with one MappingEntry."""
        data = {
            "mappings": [
                {
                    "rm_folder": "Work",
                    "rm_notebook": "Meeting Notes",
                    "notebooklm_nb_id": "nb-abc-123",
                }
            ]
        }
        yaml_file = tmp_path / "mappings.yaml"
        yaml_file.write_text(yaml.safe_dump(data))

        result = load_mappings(yaml_file)

        assert len(result) == 1
        assert isinstance(result[0], MappingEntry)
        assert result[0].rm_folder == "Work"
        assert result[0].rm_notebook == "Meeting Notes"
        assert result[0].notebooklm_nb_id == "nb-abc-123"

    def test_multiple_entries_loaded(self, tmp_path: Path) -> None:
        """Two entries in the YAML file produces a list of length 2."""
        data = {
            "mappings": [
                {
                    "rm_folder": "Work",
                    "rm_notebook": "Notes",
                    "notebooklm_nb_id": "nb-1",
                },
                {
                    "rm_folder": "Personal",
                    "rm_notebook": "Journal",
                    "notebooklm_nb_id": "nb-2",
                },
            ]
        }
        yaml_file = tmp_path / "mappings.yaml"
        yaml_file.write_text(yaml.safe_dump(data))

        result = load_mappings(yaml_file)

        assert len(result) == 2
        assert result[0].rm_notebook == "Notes"
        assert result[1].rm_notebook == "Journal"

    def test_defaults_applied(self, tmp_path: Path) -> None:
        """responses_folder defaults to 'responses' and notebooklm_path defaults to None."""
        data = {
            "mappings": [
                {
                    "rm_folder": "Work",
                    "rm_notebook": "Notes",
                    "notebooklm_nb_id": "nb-1",
                }
            ]
        }
        yaml_file = tmp_path / "mappings.yaml"
        yaml_file.write_text(yaml.safe_dump(data))

        result = load_mappings(yaml_file)

        assert result[0].responses_folder == "responses"
        assert result[0].notebooklm_path is None

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Malformed YAML raises yaml.YAMLError."""
        yaml_file = tmp_path / "mappings.yaml"
        yaml_file.write_text("mappings: [{\nbroken: yaml: :]]]")

        with pytest.raises(yaml.YAMLError):
            load_mappings(yaml_file)

    def test_missing_required_field_raises_validation_error(self, tmp_path: Path) -> None:
        """Missing rm_folder field raises pydantic.ValidationError."""
        data = {
            "mappings": [
                {
                    # rm_folder is missing
                    "rm_notebook": "Notes",
                    "notebooklm_nb_id": "nb-1",
                }
            ]
        }
        yaml_file = tmp_path / "mappings.yaml"
        yaml_file.write_text(yaml.safe_dump(data))

        with pytest.raises(ValidationError):
            load_mappings(yaml_file)

    def test_invalid_notebooklm_path_raises(self, tmp_path: Path) -> None:
        """notebooklm_path value 'Z' (not A/B/C/None) raises pydantic.ValidationError."""
        data = {
            "mappings": [
                {
                    "rm_folder": "Work",
                    "rm_notebook": "Notes",
                    "notebooklm_nb_id": "nb-1",
                    "notebooklm_path": "Z",
                }
            ]
        }
        yaml_file = tmp_path / "mappings.yaml"
        yaml_file.write_text(yaml.safe_dump(data))

        with pytest.raises(ValidationError):
            load_mappings(yaml_file)

    def test_empty_mappings_list_ok(self, tmp_path: Path) -> None:
        """mappings: [] is valid and returns an empty list."""
        data = {"mappings": []}
        yaml_file = tmp_path / "mappings.yaml"
        yaml_file.write_text(yaml.safe_dump(data))

        result = load_mappings(yaml_file)

        assert result == []

    def test_tilde_expanded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A path with ~ is expanded before checking file existence."""
        # Point ~ at tmp_path so we can create a file there
        monkeypatch.setenv("HOME", str(tmp_path))
        data = {
            "mappings": [
                {
                    "rm_folder": "Work",
                    "rm_notebook": "Notes",
                    "notebooklm_nb_id": "nb-1",
                }
            ]
        }
        yaml_file = tmp_path / "mappings.yaml"
        yaml_file.write_text(yaml.safe_dump(data))

        # Call with a tilde path
        result = load_mappings(Path("~/mappings.yaml"))

        assert len(result) == 1
        assert result[0].rm_folder == "Work"
