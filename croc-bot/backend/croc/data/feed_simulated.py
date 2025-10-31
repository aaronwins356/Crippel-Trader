"""Simulated market data feed for AI simulation mode."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

import numpy as np

from .feed_base import Feed
from ..models.types import Tick


class SimulatedFeed(Feed):
    """Generates ticks using a stochastic process with configurable noise."""

    def __init__(
        self,
        symbol: str,
        *,
        base_price: float,
        volatility: float,
        interval_seconds: float,
        seed: Optional[int] = None,
    ) -> None:
        super().__init__(symbol)
        self.base_price = base_price
        self.volatility = volatility
        self.interval = interval_seconds
        self._rng = np.random.default_rng(seed)
        self._mid = base_price
        self._running = False

    async def connect(self) -> None:
        self._running = True
        self._mid = self.base_price

    async def disconnect(self) -> None:
        self._running = False

    async def stream(self) -> AsyncIterator[Tick]:
        while True:
            if not self._running:
                break
            tick = self._next_tick()
            yield tick
            await asyncio.sleep(self.interval)

    def _next_tick(self) -> Tick:
        pct_move = float(
            np.clip(
                self._rng.normal(loc=0.0, scale=self.volatility),
                -0.05,
                0.05,
            )
        )
        self._mid = max(1.0, self._mid * (1.0 + pct_move))
        spread = max(self._mid * 0.0006, 0.5)
        drift = float(self._rng.normal(loc=0.0, scale=spread * 0.05))
        last = self._mid + drift
        volume = float(np.maximum(0.01, self._rng.lognormal(mean=-2.0, sigma=0.6)))
        return Tick(
            timestamp=datetime.now(tz=timezone.utc),
            symbol=self.symbol,
            bid=self._mid - spread / 2,
            ask=self._mid + spread / 2,
            last=max(0.1, last),
            volume=volume,
        )


__all__ = ["SimulatedFeed"]
