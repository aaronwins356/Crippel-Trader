"""Deterministic synthetic data feeds for testing and simulation."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

import numpy as np

from ..domain import MarketData
from .base import DataFeed


@dataclass(slots=True)
class SyntheticFeedConfig:
    """Configuration for the synthetic random-walk price feed."""

    symbol: str
    interval_seconds: float
    initial_price: float
    volatility: float
    seed: int

    def __post_init__(self) -> None:
        if self.interval_seconds < 0:
            raise ValueError("interval_seconds must be non-negative")
        if self.initial_price <= 0:
            raise ValueError("initial_price must be positive")
        if self.volatility < 0:
            raise ValueError("volatility must be non-negative")
        if not self.symbol:
            raise ValueError("symbol must be provided")
        if self.seed < 0:
            raise ValueError("seed must be non-negative")


class SyntheticPriceFeed(DataFeed):
    """Generates synthetic prices using a deterministic random walk."""

    def __init__(self, config: SyntheticFeedConfig) -> None:
        self._config = config
        self._rng = np.random.default_rng(config.seed)
        self._last_price = config.initial_price
        self._current_time = datetime.now(timezone.utc)
        self._lock = asyncio.Lock()

    def read(self) -> MarketData:
        change = self._rng.normal(loc=0.0, scale=self._config.volatility)
        new_price = max(1e-6, self._last_price + change)
        self._last_price = new_price
        self._current_time += timedelta(seconds=self._config.interval_seconds or 0.0)
        return MarketData(
            symbol=self._config.symbol,
            price=float(new_price),
            timestamp=self._current_time,
            raw={"change": float(change)},
        )

    async def stream(self) -> AsyncIterator[MarketData]:
        while True:
            async with self._lock:
                tick = self.read()
            yield tick
            if self._config.interval_seconds > 0:
                await asyncio.sleep(self._config.interval_seconds)
            else:
                await asyncio.sleep(0)
