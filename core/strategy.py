"""Strategy logic for CrocBot."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Deque


class TradeSignal(Enum):
    """Represents the desired trade action."""

    BUY = auto()
    SELL = auto()
    HOLD = auto()


@dataclass(frozen=True)
class StrategyConfig:
    """Configuration for the moving-average crossover strategy."""

    fast_window: int
    slow_window: int


class MovingAverageCrossoverStrategy:
    """Generates trade signals based on SMA crossover events."""

    def __init__(self, config: StrategyConfig) -> None:
        if config.fast_window <= 0 or config.slow_window <= 0:
            raise ValueError("Window sizes must be positive integers.")
        if config.fast_window >= config.slow_window:
            raise ValueError("fast_window must be less than slow_window for crossover strategy.")

        self._config = config
        self._prices: Deque[float] = deque(maxlen=config.slow_window)
        self._previous_diff: float | None = None

    def update(self, price: float) -> TradeSignal:
        """Update the strategy with the latest price and return a trade signal."""

        self._prices.append(price)
        if len(self._prices) < self._config.slow_window:
            return TradeSignal.HOLD

        fast_sma = self._simple_moving_average(self._config.fast_window)
        slow_sma = self._simple_moving_average(self._config.slow_window)

        diff = fast_sma - slow_sma
        signal = TradeSignal.HOLD

        if self._previous_diff is not None:
            if self._previous_diff <= 0 and diff > 0:
                signal = TradeSignal.BUY
            elif self._previous_diff >= 0 and diff < 0:
                signal = TradeSignal.SELL

        self._previous_diff = diff
        return signal

    def _simple_moving_average(self, window: int) -> float:
        """Compute the simple moving average for the latest *window* prices."""

        if window <= 0:
            raise ValueError("Window size must be positive.")
        if len(self._prices) < window:
            raise ValueError("Not enough data to compute SMA.")

        relevant_prices = list(self._prices)[-window:]
        return sum(relevant_prices) / window


__all__ = ["TradeSignal", "StrategyConfig", "MovingAverageCrossoverStrategy"]
