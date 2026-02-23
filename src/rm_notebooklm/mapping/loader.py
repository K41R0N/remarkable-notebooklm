"""Load and validate the notebook mappings YAML file."""

from __future__ import annotations

from pathlib import Path

import yaml

from rm_notebooklm.mapping.models import MappingEntry, MappingsConfig
from rm_notebooklm.utils.logging import get_logger

log = get_logger(__name__)


def load_mappings(path: Path) -> list[MappingEntry]:
    """Load and validate mappings.yaml.

    Args:
        path: Path to the YAML file (~ is expanded).

    Returns:
        List of validated MappingEntry instances. Empty list if the file
        does not exist.

    Raises:
        pydantic.ValidationError: If the YAML is structurally invalid.
        yaml.YAMLError: If the file is not valid YAML.
    """
    expanded = path.expanduser()
    if not expanded.exists():
        log.info("mappings_file_not_found", path=str(expanded))
        return []

    with expanded.open() as f:
        raw = yaml.safe_load(f)

    config = MappingsConfig.model_validate(raw)
    log.info("mappings_loaded", count=len(config.mappings))
    return config.mappings
