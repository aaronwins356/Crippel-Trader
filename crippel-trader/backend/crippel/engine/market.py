"""Market data ingestion layer."""
from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator, Callable

from ..logging import get_logger
from ..models.core import PriceTick


class MarketStream:
    """Asynchronously delivers price ticks to subscribers."""

    def __init__(self, history_window: int = 256) -> None:
        self._queue: asyncio.Queue[PriceTick] = asyncio.Queue(maxsize=1024)
        self._history = deque[PriceTick](maxlen=history_window)
        self._listeners: list[Callable[[PriceTick], None]] = []
        self._logger = get_logger(__name__)

    async def publish(self, tick: PriceTick) -> None:
        """Publish a tick to listeners and queue."""
        self._history.append(tick)
        for listener in self._listeners:
            listener(tick)
        await self._queue.put(tick)

    def subscribe(self, callback: Callable[[PriceTick], None]) -> None:
        self._listeners.append(callback)

    def history(self, symbol: str | None = None) -> list[PriceTick]:
        if symbol is None:
            return list(self._history)
        return [tick for tick in self._history if tick.symbol == symbol]

    async def stream(self) -> AsyncIterator[PriceTick]:
        while True:
            tick = await self._queue.get()
            yield tick


class MarketDataEngine:
    """Aggregates tick data from adapters."""

    def __init__(self, history_window: int = 256) -> None:
        self.stream = MarketStream(history_window=history_window)
        self._logger = get_logger(__name__)

    async def ingest(self, tick: PriceTick) -> None:
        self._logger.debug("ingest", symbol=tick.symbol, price=tick.price)
        await self.stream.publish(tick)
