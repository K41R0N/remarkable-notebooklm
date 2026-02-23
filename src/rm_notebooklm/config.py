"""Pydantic Settings — all configuration loaded from environment / .env file.

Usage:
    from rm_notebooklm.config import settings
    print(settings.ocr_provider)
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration. All values can be set via environment variables
    or a .env file in the working directory."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # -----------------------------------------------------------------------
    # reMarkable
    # -----------------------------------------------------------------------
    rm_device_token: str = Field(default="", description="Permanent JWT from device registration")
    rm_user_token: str = Field(default="", description="Short-lived JWT (auto-refreshed if empty)")

    # -----------------------------------------------------------------------
    # OCR
    # -----------------------------------------------------------------------
    ocr_provider: Literal["gemini", "openai", "claude"] = Field(
        default="gemini",
        description="Vision LLM provider for handwriting OCR",
    )
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    openai_api_key: str = Field(default="", description="OpenAI API key")
    anthropic_api_key: str = Field(default="", description="Anthropic API key")

    # -----------------------------------------------------------------------
    # NotebookLM path
    # -----------------------------------------------------------------------
    notebooklm_path: Literal["A", "B", "C"] = Field(
        default="C",
        description="A=unofficial notebooklm-py | B=Enterprise API | C=Gemini grounding",
    )

    # Path A: notebooklm-py
    notebooklm_auth_json: Path | None = Field(
        default=None,
        description="Path to ~/.notebooklm/storage_state.json (Path A only)",
    )

    # Path B: Enterprise API
    notebooklm_project_number: str = Field(default="", description="GCP project number")
    notebooklm_location: str = Field(default="us-central1")
    notebooklm_endpoint_location: str = Field(default="us-central1")

    # Path C: Gemini grounding
    gcs_bucket_name: str = Field(
        default="",
        description="GCS bucket for document uploads (Path C only)",
    )

    # -----------------------------------------------------------------------
    # Google Drive (Paths A and B)
    # -----------------------------------------------------------------------
    google_credentials_json: Path = Field(
        default=Path("credentials.json"),
        description="OAuth client secrets file",
    )
    google_token_json: Path = Field(
        default=Path("token.json"),
        description="Auto-managed OAuth token cache",
    )
    google_drive_folder_id: str = Field(
        default="",
        description="Target Google Drive folder ID (optional)",
    )

    # -----------------------------------------------------------------------
    # State
    # -----------------------------------------------------------------------
    state_db_path: Path = Field(
        default=Path("~/.rm_notebooklm/state.db"),
        description="SQLite database path for processed page tracking",
    )

    # -----------------------------------------------------------------------
    # Notebook mappings
    # -----------------------------------------------------------------------
    rm_notebook_mappings_file: Path = Field(
        default=Path("~/.rm_notebooklm/mappings.yaml"),
        description="Path to YAML mapping reMarkable notebooks to NotebookLM projects",
    )

    # -----------------------------------------------------------------------
    # Logging
    # -----------------------------------------------------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "text"] = "json"

    @model_validator(mode="after")
    def validate_ocr_key(self) -> Settings:
        """Warn if the selected OCR provider has no API key configured."""
        key_map = {
            "gemini": self.gemini_api_key,
            "openai": self.openai_api_key,
            "claude": self.anthropic_api_key,
        }
        if not key_map.get(self.ocr_provider):
            import warnings

            warnings.warn(
                f"OCR provider '{self.ocr_provider}' selected but corresponding API key is empty.",
                stacklevel=2,
            )
        return self

    @property
    def state_db_path_expanded(self) -> Path:
        """Return state_db_path with ~ expanded."""
        return self.state_db_path.expanduser()

    @property
    def rm_notebook_mappings_file_expanded(self) -> Path:
        """Return rm_notebook_mappings_file with ~ expanded."""
        return self.rm_notebook_mappings_file.expanduser()


# Module-level singleton — import this in all other modules.
settings = Settings()
