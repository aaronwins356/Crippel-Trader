"""Tests for the moving average strategy."""
from __future__ import annotations

from datetime import datetime, timezone

from croc_bot.domain import MarketData, TradeSignal
from croc_bot.execution.base import PortfolioState
from croc_bot.strategy import MovingAverageConfig, MovingAverageStrategy


def _portfolio_state() -> PortfolioState:
    return PortfolioState(
        cash=10_000.0,
        equity=10_000.0,
        position_units=0.0,
        position_value=0.0,
        avg_entry_price=None,
        peak_equity=10_000.0,
        drawdown=0.0,
        timestamp=datetime.now(timezone.utc),
    )


def _market(price: float) -> MarketData:
    return MarketData(symbol="TEST", price=price, timestamp=datetime.now(timezone.utc))


def test_moving_average_crossover_signals() -> None:
    """Strategy should emit BUY then SELL when SMAs cross."""

    strategy = MovingAverageStrategy(MovingAverageConfig(fast_window=2, slow_window=4))
    prices = [100.0, 99.0, 98.0, 97.0, 110.0, 95.0, 90.0]

    actions = [strategy.on_market_data(_market(price), _portfolio_state()) for price in prices]

    assert actions[4].signal == TradeSignal.BUY
    assert actions[-1].signal == TradeSignal.SELL
