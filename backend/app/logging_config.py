"""Centralised logging configuration for the application."""
from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging with a single stdout handler."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Keep access logs readable at INFO.
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger (caller is responsible for prior configure_logging)."""
    return logging.getLogger(name)