"""Placeholder adapter for future stock integrations."""
from __future__ import annotations

from collections.abc import AsyncIterator

from ..models.core import Order, PriceTick
from .base import ExchangeAdapter


class StocksAdapter(ExchangeAdapter):
    """Stub adapter that raises informative errors."""

    async def connect_market_data(self, symbols: list[str]) -> AsyncIterator[PriceTick]:
        raise NotImplementedError("StocksAdapter is a stub and does not provide market data yet")

    async def submit_order(self, order: Order) -> None:
        raise NotImplementedError("StocksAdapter is a stub and cannot submit orders yet")

    async def close(self) -> None:
        return None
