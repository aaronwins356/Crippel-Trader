"""Deterministic market data simulator."""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List

from ..logging import get_logger


@dataclass
class MarketTick:
    ts: int
    price: float
    volume: float


@dataclass
class SimulatedMarketData:
    """Generates repeatable pseudo price paths for symbols."""

    seed: int = 42
    base_prices: Dict[str, float] = field(default_factory=lambda: {"BTC-USD": 40000.0, "ETH-USD": 2000.0})

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self._ticks: Dict[str, List[MarketTick]] = {symbol: [] for symbol in self.base_prices}
        self._logger = get_logger("market")
        for symbol in self.base_prices:
            self._ticks[symbol].append(MarketTick(ts=self._now(), price=self.base_prices[symbol], volume=1.0))

    def _now(self) -> int:
        return int(time.time() * 1000)

    def advance_time(self) -> None:
        for symbol, base in self.base_prices.items():
            series = self._ticks[symbol]
            last_price = series[-1].price
            t = len(series)
            drift = math.sin(t / 20) * base * 0.0005
            noise = self._rng.normalvariate(0, base * 0.0008)
            price = max(1.0, last_price + drift + noise)
            volume = abs(self._rng.normalvariate(3.0, 1.0))
            series.append(MarketTick(ts=self._now(), price=price, volume=volume))
        self._logger.debug("advance_time")

    def current_price(self, symbol: str) -> float:
        series = self._ticks.setdefault(symbol, [MarketTick(ts=self._now(), price=self.base_prices.get(symbol, 100.0), volume=1.0)])
        return series[-1].price

    def history(self, symbol: str, limit: int = 200) -> List[MarketTick]:
        series = self._ticks.setdefault(symbol, [MarketTick(ts=self._now(), price=self.base_prices.get(symbol, 100.0), volume=1.0)])
        return series[-limit:]

    def snapshot(self) -> Dict[str, MarketTick]:
        return {symbol: ticks[-1] for symbol, ticks in self._ticks.items()}
