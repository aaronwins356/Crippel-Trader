"""Moving average crossover strategy."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque

import numpy as np

from ..domain import TradeAction, TradeSignal
from ..execution.base import PortfolioState
from ..domain import MarketData
from .base import BaseStrategy, StrategyConfig


@dataclass(slots=True)
class MovingAverageConfig(StrategyConfig):
    """Configuration for the moving-average crossover strategy."""

    fast_window: int
    slow_window: int
    target_notional: float | None = None

    def __post_init__(self) -> None:
        if self.fast_window <= 0 or self.slow_window <= 0:
            raise ValueError("Window sizes must be positive integers")
        if self.fast_window >= self.slow_window:
            raise ValueError("fast_window must be smaller than slow_window")
        if self.target_notional is not None and self.target_notional <= 0:
            raise ValueError("target_notional must be positive when provided")


class MovingAverageStrategy(BaseStrategy):
    """Momentum strategy that reacts to SMA crossovers."""

    def __init__(self, config: MovingAverageConfig) -> None:
        super().__init__(config)
        self._config = config
        self._prices: Deque[float] = deque(maxlen=config.slow_window)
        self._previous_diff: float | None = None

    def on_market_data(self, market: MarketData, portfolio: PortfolioState) -> TradeAction:
        self._prices.append(market.price)
        if len(self._prices) < self._config.slow_window:
            return TradeAction(signal=TradeSignal.HOLD, metadata={"reason": "warmup"})

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
        notional = self._config.target_notional
        metadata = {
            "fast_sma": fast_sma,
            "slow_sma": slow_sma,
            "diff": diff,
        }
        return TradeAction(signal=signal, notional=notional, metadata=metadata)

    def _simple_moving_average(self, window: int) -> float:
        if window <= 0:
            raise ValueError("window must be positive")
        if len(self._prices) < window:
            raise ValueError("not enough prices to compute SMA")
        array = np.fromiter(self._prices, dtype=float)[-window:]
        return float(array.mean())
