"""Structured logging utilities."""

from __future__ import annotations

import logging
from logging.config import dictConfig
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

try:
    import orjson
except ModuleNotFoundError:  # pragma: no cover - fallback for tests
    import json

    class _Orjson:
        @staticmethod
        def dumps(data: dict) -> bytes:
            return json.dumps(data).encode("utf-8")

    orjson = _Orjson()


class OrjsonFormatter(logging.Formatter):
    """Minimal JSON formatter using orjson."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - simple formatting
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = record.stack_info
        for key in ("request_id", "symbol", "mode", "loop_ms", "latency_ms"):
            if key in record.__dict__ and record.__dict__[key] is not None:
                payload[key] = record.__dict__[key]
        return orjson.dumps(payload).decode("utf-8")


def configure_logging(log_level: str, storage_dir: Path) -> None:
    """Configure rotating structured logs for the service."""

    storage_dir.mkdir(parents=True, exist_ok=True)
    logfile = storage_dir / "croc.log"

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": OrjsonFormatter,
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "level": log_level,
                },
                "file": {
                    "()": RotatingFileHandler,
                    "formatter": "json",
                    "level": log_level,
                    "filename": str(logfile),
                    "maxBytes": 5 * 1024 * 1024,
                    "backupCount": 3,
                },
            },
            "root": {
                "handlers": ["console", "file"],
                "level": log_level,
            },
            "loggers": {
                "uvicorn": {"level": log_level, "handlers": ["console", "file"], "propagate": False},
                "uvicorn.error": {
                    "level": log_level,
                    "handlers": ["console", "file"],
                    "propagate": False,
                },
                "uvicorn.access": {
                    "level": log_level,
                    "handlers": ["console", "file"],
                    "propagate": False,
                },
            },
        }
    )


__all__ = ["configure_logging"]
