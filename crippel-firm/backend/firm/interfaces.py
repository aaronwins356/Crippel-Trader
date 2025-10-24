"""Protocol definitions for firm components."""
from __future__ import annotations

import asyncio
from typing import Any, Protocol, runtime_checkable

MetricDict = dict[str, float]


@runtime_checkable
class EventBusProtocol(Protocol):
    """Protocol describing the event bus interface."""

    async def subscribe(self, topic: str) -> asyncio.Queue[Any]:
        ...

    async def unsubscribe(self, topic: str, queue: asyncio.Queue[Any]) -> None:
        ...

    async def publish(self, topic: str, payload: Any) -> None:
        ...

    def stats(self) -> dict[str, Any]:
        ...


@runtime_checkable
class BotProtocol(Protocol):
    """Protocol implemented by worker bots."""

    bot_id: str
    bot_type: str
    last_active: float

    async def start(self) -> None:
        ...

    async def stop(self) -> None:
        ...

    async def on_tick(self) -> None:
        ...

    async def on_evaluate(self) -> MetricDict:
        ...


class PerformanceModel(Protocol):
    """Protocol for performance tracking stores."""

    def record(self, bot_id: str, metric: str, value: float) -> None:
        ...

    def fetch(self, bot_id: str) -> dict[str, float]:
        ...

    def summary(self) -> dict[str, dict[str, float]]:
        ...
