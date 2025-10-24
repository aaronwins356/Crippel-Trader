"""Base class for worker bots."""
from __future__ import annotations

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Optional

from ..firm.interfaces import EventBusProtocol, MetricDict
from ..firm.economy import PerformanceLedger
from ..logging import get_logger


class WorkerBot(ABC):
    """Abstract bot with lifecycle helpers."""

    bot_type: str = "worker"

    def __init__(self, event_bus: EventBusProtocol, ledger: PerformanceLedger) -> None:
        self.bot_id = uuid.uuid4().hex
        self.event_bus = event_bus
        self.ledger = ledger
        self.last_active: float = time.time()
        self._running = asyncio.Event()
        self._task: Optional[asyncio.Task[None]] = None
        self.logger = get_logger(f"bot.{self.bot_type}", bot_id=self.bot_id)

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        await self.on_start()
        self._running.set()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._running.clear()
        if self._task:
            await self._task

    async def _run_loop(self) -> None:
        try:
            while self._running.is_set():
                try:
                    await self.on_tick()
                    self.last_active = time.time()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # pragma: no cover - logged and continues
                    self.logger.error("tick_error", error=str(exc))
                    await asyncio.sleep(0.5)
        finally:
            try:
                await self.on_terminate()
            except Exception as exc:  # pragma: no cover
                self.logger.error("terminate_error", error=str(exc))

    async def publish(self, topic: str, payload: Any) -> None:
        await self.event_bus.publish(topic, payload)

    async def subscribe(self, topic: str) -> asyncio.Queue[Any]:
        return await self.event_bus.subscribe(topic)

    async def unsubscribe(self, topic: str, queue: asyncio.Queue[Any]) -> None:
        await self.event_bus.unsubscribe(topic, queue)

    def record_metric(self, metric: str, value: float) -> None:
        self.ledger.record(self.bot_id, metric, value)

    async def on_start(self) -> None:  # pragma: no cover - optional
        """Called before the bot loop starts."""

    async def on_tick(self) -> None:
        """Main work cycle invoked repeatedly."""

    @abstractmethod
    async def on_evaluate(self) -> MetricDict:
        """Return metrics for scoring."""

    async def on_terminate(self) -> None:  # pragma: no cover - optional
        """Cleanup hook when bot stops."""


def ensure_background(task: asyncio.Task[Any]) -> None:
    """Ensure background tasks raise exceptions."""

    def _done_callback(done: asyncio.Task[Any]) -> None:
        try:
            done.result()
        except asyncio.CancelledError:  # pragma: no cover
            pass
        except Exception as exc:  # pragma: no cover
            get_logger("bot").error("background_task", error=str(exc))

    task.add_done_callback(_done_callback)
