"""Abstract base class for worker bots."""
from __future__ import annotations

import abc
import asyncio
import time
import uuid
from typing import Any, Optional

from ..eventbus import EventBus
from ..interfaces import BotProtocol
from ..utils.logging import get_logger
from ..utils.metrics import PerformanceLedger


class WorkerBot(BotProtocol, metaclass=abc.ABCMeta):
    """Base class implementing lifecycle helpers."""

    def __init__(
        self,
        event_bus: EventBus,
        performance_ledger: PerformanceLedger,
        bot_type: str,
        name: Optional[str] = None,
    ) -> None:
        self.event_bus = event_bus
        self.performance_ledger = performance_ledger
        self.bot_type = bot_type
        self.bot_id = name or str(uuid.uuid4())
        self.logger = get_logger(f"bot.{self.bot_type}.{self.bot_id}")
        self._last_active: float = time.time()
        self._task: Optional[asyncio.Task[None]] = None
        self._running = asyncio.Event()

    @property
    def last_active(self) -> float:
        return self._last_active

    async def start(self) -> None:
        """Start the bot loop."""
        if self._task and not self._task.done():
            return
        self._running.set()
        await self.on_start()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the bot."""
        self._running.clear()
        if self._task:
            await self._task
            await self.on_terminate()
            
    async def _run_loop(self) -> None:
        while self._running.is_set():
            await self.on_tick()
            self._last_active = time.time()
            await asyncio.sleep(1)

    def record_metric(self, metric: str, value: float) -> None:
        self.performance_ledger.record_event(self.bot_id, metric, value)

    @abc.abstractmethod
    async def on_start(self) -> None:
        ...

    @abc.abstractmethod
    async def on_tick(self) -> None:
        ...

    @abc.abstractmethod
    async def on_evaluate(self) -> dict[str, float]:
        ...

    @abc.abstractmethod
    async def on_terminate(self) -> None:
        ...

    # Convenience for subclasses
    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        await self.event_bus.publish(topic, payload)

    async def subscribe(self, topic: str) -> asyncio.Queue[dict[str, Any]]:
        return await self.event_bus.subscribe(topic)

    async def unsubscribe(self, topic: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        await self.event_bus.unsubscribe(topic, queue)
