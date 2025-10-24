"""Asynchronous clock driving the trading engine."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from datetime import datetime, timedelta

from ..logging import get_logger


class EngineClock:
    """Periodic ticker implemented with asyncio."""

    def __init__(self, interval_ms: int) -> None:
        self._interval = interval_ms / 1000
        self._subscribers: list[Callable[[datetime], None]] = []
        self._running = False
        self._logger = get_logger(__name__)

    def subscribe(self, callback: Callable[[datetime], None]) -> None:
        self._subscribers.append(callback)

    async def ticks(self) -> AsyncIterator[datetime]:
        """Yield timestamps at the configured interval."""
        self._running = True
        next_tick = datetime.utcnow()
        try:
            while self._running:
                now = datetime.utcnow()
                if now < next_tick:
                    await asyncio.sleep((next_tick - now).total_seconds())
                else:
                    next_tick = now
                yield now
                for callback in self._subscribers:
                    callback(now)
                next_tick += timedelta(seconds=self._interval)
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False
        self._logger.info("engine clock stopped")
