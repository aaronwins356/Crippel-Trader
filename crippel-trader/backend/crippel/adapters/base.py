"""Base exchange adapter interface."""
from __future__ import annotations

import abc
from collections.abc import AsyncIterator

from ..models.core import Order, PriceTick


class ExchangeAdapter(abc.ABC):
    """Abstract adapter for market data and order routing."""

    @abc.abstractmethod
    async def connect_market_data(self, symbols: list[str]) -> AsyncIterator[PriceTick]:
        """Return an async iterator of price ticks."""

    @abc.abstractmethod
    async def submit_order(self, order: Order) -> None:
        """Submit an order to the exchange."""

    @abc.abstractmethod
    async def close(self) -> None:
        """Cleanup resources."""
