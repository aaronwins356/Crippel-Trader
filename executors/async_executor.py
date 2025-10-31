"""Async execution clients and order flow management."""
from __future__ import annotations

import abc
import asyncio
import contextlib
from dataclasses import dataclass
from typing import AsyncIterator, Protocol

import pandas as pd

from strategies.base import Signal


class ExecutionClient(Protocol):
    """Protocol describing minimal order execution surface."""

    async def submit_order(self, order: "Order") -> "OrderAck":
        ...

    async def cancel(self, order_id: str) -> None:
        ...


@dataclass(slots=True)
class Order:
    """Internal representation of an order request."""

    signal: Signal
    price: float | None = None


@dataclass(slots=True)
class OrderAck:
    """Acknowledgement from the execution venue."""

    order_id: str
    accepted: bool
    reason: str | None = None


class OrderExecutor(abc.ABC):
    """Abstract base class for asynchronously handling orders."""

    def __init__(self, client: ExecutionClient, max_concurrency: int = 10) -> None:
        self._client = client
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def submit(self, order: Order) -> OrderAck:
        async with self._semaphore:
            return await self._client.submit_order(order)

    @abc.abstractmethod
    async def on_signal(self, signal: Signal, market_data: pd.DataFrame) -> OrderAck:
        """Convert signals into executable orders."""


class MarketOrderExecutor(OrderExecutor):
    """Submit market orders with backpressure-aware queueing."""

    def __init__(self, client: ExecutionClient, *, queue_size: int = 100) -> None:
        super().__init__(client)
        self._queue: asyncio.Queue[tuple[Signal, pd.DataFrame]] = asyncio.Queue(queue_size)
        self._ack_queue: asyncio.Queue[tuple[Signal, OrderAck]] = asyncio.Queue(queue_size)
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self) -> None:
        while True:
            signal, data = await self._queue.get()
            order = Order(signal=signal, price=float(data["close"].iloc[-1]))
            ack = await self.submit(order)
            await self._ack_queue.put((signal, ack))

    async def on_signal(self, signal: Signal, market_data: pd.DataFrame) -> OrderAck:
        await self._queue.put((signal, market_data))
        return OrderAck(order_id="queued", accepted=True)

    async def stream(self) -> AsyncIterator[tuple[Signal, OrderAck]]:
        """Yield acknowledgements as they are processed."""

        if self._task is None:
            raise RuntimeError("Executor not started")

        while True:
            yield await self._ack_queue.get()
