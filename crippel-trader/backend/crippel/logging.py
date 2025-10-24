"""Logging utilities for the Crippel engine."""
from __future__ import annotations

import logging
from typing import Any

import structlog


def configure_logging(level: int = logging.INFO) -> None:
    """Configure standard logging and structlog for structured output."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str, **kwargs: Any) -> structlog.stdlib.BoundLogger:
    """Return a structured logger bound with default metadata."""
    logger = structlog.get_logger(name)
    if kwargs:
        return logger.bind(**kwargs)
    return logger
