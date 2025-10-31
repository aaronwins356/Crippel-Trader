"""Market data feed simulation for CrocBot."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterator

import numpy as np


@dataclass(frozen=True)
class FeedConfig:
    """Configuration parameters for the synthetic market data feed."""

    symbol: str
    interval_seconds: int
    initial_price: float
    volatility: float
    seed: int


@dataclass(frozen=True)
class MarketData:
    """Represents a single market data tick."""

    symbol: str
    price: float
    timestamp: datetime


class PriceFeed:
    """Generates deterministic synthetic prices using a random walk."""

    def __init__(self, config: FeedConfig) -> None:
        self._config = config
        self._rng = np.random.default_rng(config.seed)
        self._last_price = max(0.01, config.initial_price)
        self._current_time = datetime.now(timezone.utc)

    def stream(self) -> Iterator[MarketData]:
        """Yield an infinite stream of market data ticks."""

        while True:
            yield self.read()

    def read(self) -> MarketData:
        """Generate the next market data tick."""

        change = self._rng.normal(loc=0.0, scale=self._config.volatility)
        new_price = max(0.01, self._last_price + change)
        self._last_price = new_price
        self._current_time += timedelta(seconds=self._config.interval_seconds)

        return MarketData(
            symbol=self._config.symbol,
            price=float(new_price),
            timestamp=self._current_time,
        )


__all__ = ["FeedConfig", "MarketData", "PriceFeed"]
