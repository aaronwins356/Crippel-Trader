"""Central logging configuration for the Python backend."""

from __future__ import annotations

import logging
import os
from typing import Any

_LOG_LEVEL = os.getenv("CRIPPEL_LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=_LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("crippel-trader")


def get_child(name: str) -> logging.Logger:
    """Return a child logger bound to the project namespace."""

    return logger.getChild(name)


__all__ = ["logger", "get_child"]
