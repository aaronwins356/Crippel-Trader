"""Async publish/subscribe event bus."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any


class EventBus:
    """Lightweight asyncio event bus for ticks, fills, metrics."""

    def __init__(self) -> None:
        self._topics: dict[str, set[asyncio.Queue[Any]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def publish(self, topic: str, item: Any) -> None:
        async with self._lock:
            queues = list(self._topics.get(topic, set()))
        for queue in queues:
            if queue.full():
                continue
            queue.put_nowait(item)

    @asynccontextmanager
    async def subscribe(self, topic: str, *, max_queue: int = 1024) -> AsyncIterator[asyncio.Queue[Any]]:
        queue: asyncio.Queue[Any] = asyncio.Queue(max_queue)
        async with self._lock:
            self._topics[topic].add(queue)
        try:
            yield queue
        finally:
            async with self._lock:
                self._topics[topic].discard(queue)

    async def close(self) -> None:
        async with self._lock:
            topics = list(self._topics.items())
            self._topics.clear()
        for _, queues in topics:
            for queue in queues:
                queue.put_nowait(None)


__all__ = ["EventBus"]
