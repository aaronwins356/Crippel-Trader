"""Protocol definitions for the firm."""
from __future__ import annotations

import asyncio
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EventBusProtocol(Protocol):
    """Protocol for event bus implementation."""

    async def publish(self, topic: str, payload: dict[str, Any]) -> None: ...

    async def subscribe(self, topic: str) -> asyncio.Queue[dict[str, Any]]: ...

    async def unsubscribe(self, topic: str, queue: asyncio.Queue[dict[str, Any]]) -> None: ...


@runtime_checkable
class BotProtocol(Protocol):
    """Protocol for worker bots."""

    bot_id: str
    bot_type: str
    last_active: float

    async def on_start(self) -> None: ...

    async def on_tick(self) -> None: ...

    async def on_evaluate(self) -> dict[str, float]: ...

    async def on_terminate(self) -> None: ...


@runtime_checkable
class PerformanceModel(Protocol):
    """Protocol for bot performance snapshots."""

    def record_event(self, bot_id: str, metric: str, value: float) -> None: ...

    def get_bot_summary(self, bot_id: str) -> dict[str, float]: ...

    def all_summaries(self) -> dict[str, dict[str, float]]: ...
