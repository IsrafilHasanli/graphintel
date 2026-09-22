"""Structured, OpenTelemetry-friendly logging setup."""
from __future__ import annotations

import logging

import structlog

from app.config import get_settings

_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", level=level)
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level),
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.JSONRenderer(),
        ],
    )
    _configured = True


def get_logger(name: str = "graphintel") -> structlog.stdlib.BoundLogger:
    configure_logging()
    return structlog.get_logger(name)
