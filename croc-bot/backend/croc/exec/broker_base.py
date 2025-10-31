"""Abstract broker interface."""

from __future__ import annotations

import abc
from typing import Iterable

from ..models.types import Fill, Order


class Broker(abc.ABC):
    @abc.abstractmethod
    async def submit(self, order: Order) -> Fill:
        """Submit an order and return a fill (simulated or real)."""

    @abc.abstractmethod
    async def cancel_all(self) -> None:
        """Cancel any resting orders."""

    async def bulk_submit(self, orders: Iterable[Order]) -> list[Fill]:
        fills: list[Fill] = []
        for order in orders:
            fills.append(await self.submit(order))
        return fills


__all__ = ["Broker"]
