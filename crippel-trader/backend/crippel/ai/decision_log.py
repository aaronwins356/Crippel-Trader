"""Structured logging utilities for AI assistant decisions."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DecisionLogger:
    """Persist AI reasoning and actions in JSONL format."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def log_event(self, event: str, payload: dict[str, Any]) -> None:
        """Write a single structured event to disk."""
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "payload": payload,
        }
        async with self._lock:
            await asyncio.to_thread(self._append, entry)

    def _append(self, entry: dict[str, Any]) -> None:
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, default=self._default) + "\n")

    @staticmethod
    def _default(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)


__all__ = ["DecisionLogger"]
