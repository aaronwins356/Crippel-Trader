"""Market data simulator."""
from __future__ import annotations

import math
import random
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Deque, Dict


class SimulatedMarketData:
    """Generates pseudo-random walk prices for symbols."""

    def __init__(self) -> None:
        self._prices: Dict[str, float] = defaultdict(lambda: 30_000.0)
        self._history: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=500))

    def step(self, symbol: str) -> float:
        price = self._prices[symbol]
        drift = math.sin(datetime.utcnow().timestamp() / 120) * 50
        shock = random.gauss(0, 25)
        new_price = max(price + drift + shock, 1.0)
        self._prices[symbol] = new_price
        history = self._history[symbol]
        history.append(new_price)
        return new_price

    def current_price(self, symbol: str) -> float:
        if not self._history[symbol]:
            self._history[symbol].append(self._prices[symbol])
        return self._history[symbol][-1]

    def price_history(self, symbol: str, lookback: int) -> list[float]:
        history = list(self._history[symbol])
        if not history:
            history.append(self._prices[symbol])
        while len(history) < lookback:
            history.append(history[-1])
        return history[-lookback:]

    def advance_time(self, seconds: float = 1.0) -> None:
        for symbol in list(self._prices.keys()):
            self.step(symbol)
