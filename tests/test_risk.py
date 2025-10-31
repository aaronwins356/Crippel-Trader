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


def test_risk_enforces_daily_loss_limit() -> None:
    config = SimpleRiskConfig(
        max_drawdown=0.3,
        stop_loss_pct=0.05,
        position_size_pct=0.2,
        max_position_value=5_000.0,
        daily_loss_limit=500.0,
    )
    manager = SimpleRiskManager(config)
    portfolio = PortfolioState(
        cash=5_000.0,
        equity=4_400.0,
        position_units=0.0,
        position_value=0.0,
        avg_entry_price=None,
        peak_equity=5_000.0,
        drawdown=0.05,
        timestamp=datetime.now(timezone.utc),
    )

    action = manager.evaluate(TradeAction(signal=TradeSignal.BUY, notional=1_000.0), _market(100.0), portfolio)
    assert action.signal == TradeSignal.HOLD
    assert action.metadata["reason"] == "daily_loss_limit"


def test_probation_reduces_position_size() -> None:
    config = SimpleRiskConfig(
        max_drawdown=0.3,
        stop_loss_pct=0.05,
        position_size_pct=0.5,
        max_position_value=50_000.0,
        probation_position_pct=0.1,
    )
    manager = SimpleRiskManager(config)
    portfolio = PortfolioState(
        cash=100_000.0,
        equity=100_000.0,
        position_units=0.0,
        position_value=0.0,
        avg_entry_price=None,
        peak_equity=100_000.0,
        drawdown=0.0,
        timestamp=datetime.now(timezone.utc),
    )

    raw_action = TradeAction(signal=TradeSignal.BUY, notional=40_000.0, metadata={"deployment_stage": "probation"})
    adjusted = manager.evaluate(raw_action, _market(100.0), portfolio)
    assert adjusted.signal == TradeSignal.BUY
    assert adjusted.notional == 10_000.0
