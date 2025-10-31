"""Tests for risk management."""
from __future__ import annotations

from datetime import datetime, timezone

from croc_bot.domain import MarketData, TradeAction, TradeSignal
from croc_bot.execution.base import PortfolioState
from croc_bot.risk import SimpleRiskConfig, SimpleRiskManager


RISK_CONFIG = SimpleRiskConfig(
    max_drawdown=0.2,
    stop_loss_pct=0.05,
    position_size_pct=0.1,
    max_position_value=1_000.0,
)


def _market(price: float) -> MarketData:
    return MarketData(symbol="TEST", price=price, timestamp=datetime.now(timezone.utc))


def test_risk_blocks_trading_on_drawdown() -> None:
    """Risk manager should halt trading when drawdown exceeds the limit."""

    manager = SimpleRiskManager(RISK_CONFIG)
    portfolio = PortfolioState(
        cash=5_000.0,
        equity=4_000.0,
        position_units=0.0,
        position_value=0.0,
        avg_entry_price=None,
        peak_equity=5_000.0,
        drawdown=0.25,
        timestamp=datetime.now(timezone.utc),
    )

    action = manager.evaluate(TradeAction(signal=TradeSignal.BUY, notional=500.0), _market(100.0), portfolio)
    assert action.signal == TradeSignal.HOLD
    assert action.notional is None or action.notional == 0.0


def test_risk_triggers_stop_loss_exit() -> None:
    """Risk manager should enforce stop-loss exits."""

    manager = SimpleRiskManager(RISK_CONFIG)
    portfolio = PortfolioState(
        cash=5_000.0,
        equity=9_000.0,
        position_units=10.0,
        position_value=940.0,
        avg_entry_price=100.0,
        peak_equity=9_500.0,
        drawdown=0.05,
        timestamp=datetime.now(timezone.utc),
    )

    action = manager.evaluate(TradeAction(signal=TradeSignal.HOLD), _market(94.0), portfolio)
    assert action.signal == TradeSignal.SELL
    assert action.notional == portfolio.position_units * 94.0
