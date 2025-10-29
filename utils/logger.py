"""Logging utilities for Croc-Bot."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_LOGGER_CACHE: dict[str, logging.Logger] = {}


def get_logger(name: str, log_dir: Path, level: str = "INFO", retention: int = 7) -> logging.Logger:
    """Return a configured rotating logger instance.

    Parameters
    ----------
    name:
        Logger name.
    log_dir:
        Directory where log files are stored.
    level:
        Logging level name.
    retention:
        Number of rotating backups to keep.
    """
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{name}.log"

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=max(1, retention))
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)

    _LOGGER_CACHE[name] = logger
    return logger


def reset_logger(name: Optional[str] = None) -> None:
    """Reset cached loggers, useful for testing."""
    if name:
        logger = _LOGGER_CACHE.pop(name, None)
        if logger:
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)
        return

    for logger in list(_LOGGER_CACHE.values()):
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
    _LOGGER_CACHE.clear()
