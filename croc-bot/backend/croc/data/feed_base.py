"""Abstract feed definitions."""

from __future__ import annotations

import abc
from collections.abc import AsyncIterator

from ..models.types import Tick


class Feed(abc.ABC):
    """Abstract base class for market data feeds."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    @abc.abstractmethod
    async def connect(self) -> None:
        """Connect to the data source."""

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the data source."""

    @abc.abstractmethod
    def stream(self) -> AsyncIterator[Tick]:
        """Return an async iterator of ticks."""


__all__ = ["Feed"]
