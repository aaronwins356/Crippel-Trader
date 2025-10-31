"""Tests for strategy module."""
from __future__ import annotations

from core.strategy import (
    MovingAverageCrossoverStrategy,
    StrategyConfig,
    TradeSignal,
)


def test_moving_average_crossover_signals() -> None:
    """Strategy should emit BUY then SELL when SMAs cross."""

    strategy = MovingAverageCrossoverStrategy(StrategyConfig(fast_window=2, slow_window=4))
    prices = [100.0, 99.0, 98.0, 97.0, 110.0, 95.0, 90.0]

    signals = [strategy.update(price) for price in prices]

    assert signals[4] == TradeSignal.BUY
    assert signals[-1] == TradeSignal.SELL
