"""Asynchronous publish/subscribe event bus with bounded queues."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Dict, Set

from ..logging import get_logger

QueueSet = Set[asyncio.Queue[Any]]


class EventBus:
    """Simple bounded publish/subscribe event bus."""

    def __init__(self, max_queue_size: int = 100) -> None:
        self._topics: Dict[str, QueueSet] = defaultdict(set)
        self._max_queue_size = max_queue_size
        self._dropped: Dict[str, int] = defaultdict(int)
        self._logger = get_logger("eventbus")
        self._lock = asyncio.Lock()

    async def subscribe(self, topic: str) -> asyncio.Queue[Any]:
        """Register a subscriber for a topic and return its queue."""

        queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=self._max_queue_size)
        async with self._lock:
            self._topics[topic].add(queue)
        self._logger.debug("Subscribed to %s", topic)
        return queue

    async def unsubscribe(self, topic: str, queue: asyncio.Queue[Any]) -> None:
        """Remove a subscriber from a topic."""

        async with self._lock:
            queues = self._topics.get(topic)
            if not queues:
                return
            queues.discard(queue)
            if not queues:
                self._topics.pop(topic, None)
        self._logger.debug("Unsubscribed from %s", topic)

    async def publish(self, topic: str, payload: Any) -> None:
        """Publish a payload to all subscribers of a topic."""

        async with self._lock:
            queues = list(self._topics.get(topic, set()))
        if not queues:
            return
        for queue in queues:
            while queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                else:
                    self._dropped[topic] += 1
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                self._dropped[topic] += 1
                self._logger.warning("Queue still full for topic %s", topic)
        self._logger.debug("Published to %s", topic)

    def stats(self) -> dict[str, Any]:
        """Return queue statistics useful for monitoring."""

        return {
            "topics": {topic: len(queues) for topic, queues in self._topics.items()},
            "dropped": dict(self._dropped),
        }
