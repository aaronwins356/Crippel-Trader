"""Tests for risk management."""
from __future__ import annotations

from core.risk import AccountState, RiskConfig, RiskManager
from core.strategy import TradeSignal


RISK_CONFIG = RiskConfig(
    max_drawdown=0.2,
    stop_loss_pct=0.05,
    position_size_pct=0.1,
    max_position_value=1_000.0,
)


def test_risk_blocks_trading_on_drawdown() -> None:
    """Risk manager should halt trading when drawdown exceeds the limit."""

    manager = RiskManager(RISK_CONFIG)
    account = AccountState(
        cash=5_000.0,
        equity=4_000.0,
        position_units=0.0,
        position_value=0.0,
        avg_entry_price=None,
        peak_equity=5_000.0,
        drawdown=0.25,
    )

    decision = manager.assess(TradeSignal.BUY, price=100.0, account=account)
    assert decision.signal == TradeSignal.HOLD
    assert decision.notional_value == 0.0


def test_risk_triggers_stop_loss_exit() -> None:
    """Risk manager should enforce stop-loss exits."""

    manager = RiskManager(RISK_CONFIG)
    account = AccountState(
        cash=5_000.0,
        equity=9_000.0,
        position_units=10.0,
        position_value=940.0,
        avg_entry_price=100.0,
        peak_equity=9_500.0,
        drawdown=0.05,
    )

    decision = manager.assess(TradeSignal.HOLD, price=94.0, account=account)
    assert decision.signal == TradeSignal.SELL
    assert decision.notional_value == 940.0
