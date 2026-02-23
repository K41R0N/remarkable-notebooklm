"""structlog JSON structured logging setup.

Usage:
    from rm_notebooklm.utils.logging import get_logger

    log = get_logger(__name__)
    log = log.bind(page_id="abc123", notebook="My Notes")
    log.info("ocr_complete", char_count=512, provider="gemini")
"""

from __future__ import annotations

import logging
from typing import Any

import structlog


def configure_logging(level: str = "INFO", fmt: str = "json") -> None:
    """Initialize structlog with JSON or human-readable output.

    Call once at application startup (in CLI entry point).

    Args:
        level: Log level string (DEBUG/INFO/WARNING/ERROR).
        fmt: "json" for production, "text" for development.
    """
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    if fmt == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))


def get_logger(name: str) -> Any:
    """Get a bound structlog logger.

    Args:
        name: Logger name (typically __name__).

    Returns:
        structlog BoundLogger instance.
    """
    return structlog.get_logger(name)
