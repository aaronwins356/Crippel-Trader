"""Async event bus for inter-bot communication."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, DefaultDict

from .interfaces import EventBusProtocol


class EventBus(EventBusProtocol):
    """Simple topic-based pub/sub using asyncio queues."""

    def __init__(self) -> None:
        self._queues: DefaultDict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            queues = list(self._queues.get(topic, set()))
        for queue in queues:
            await queue.put(payload)

    async def subscribe(self, topic: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        async with self._lock:
            self._queues[topic].add(queue)
        return queue

    async def unsubscribe(self, topic: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            if queue in self._queues.get(topic, set()):
                self._queues[topic].remove(queue)
            if not self._queues[topic]:
                self._queues.pop(topic, None)
