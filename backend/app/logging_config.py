"""Structured logging configuration for BMKG Alert."""

from __future__ import annotations

import logging
import sys

import structlog


def setup_logging(log_level: str = "info") -> None:
    """Configure structlog with JSON output for production, pretty for dev."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    is_dev = log_level.lower() in ("debug", "info")

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    renderer = (
        structlog.dev.ConsoleRenderer()
        if is_dev
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging for uvicorn/httpx
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )
