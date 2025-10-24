"""Logging helpers."""
from __future__ import annotations

import logging
from logging import Logger


def configure_logging(level: int = logging.INFO) -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )


def get_logger(name: str) -> Logger:
    """Return a configured logger."""
    return logging.getLogger(name)
