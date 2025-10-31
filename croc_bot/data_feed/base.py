"""Abstract interfaces for market data ingestion."""
from __future__ import annotations

import abc
from typing import AsyncIterator

from ..domain import MarketData


class DataFeed(abc.ABC):
    """Abstract base class describing a source of market data ticks."""

    @abc.abstractmethod
    async def stream(self) -> AsyncIterator[MarketData]:
        """Return an asynchronous iterator of market data updates."""

    @abc.abstractmethod
    def read(self) -> MarketData:
        """Synchronously return the next market data tick."""
