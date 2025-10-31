"""Tests for performance monitoring and experience logging."""
from __future__ import annotations

from datetime import datetime, timezone

from data.experience import FileExperienceRepository
from data.performance import FilePerformanceRepository, PerformanceAccumulator

from croc_bot.domain import MarketData, TradeAction, TradeSignal
from croc_bot.execution.base import ExecutionResult, OrderStatus, PortfolioState
from croc_bot.monitoring.performance import PerformanceMonitor


def _portfolio(equity: float, cash: float, position_units: float = 0.0) -> PortfolioState:
    return PortfolioState(
        cash=cash,
        equity=equity,
        position_units=position_units,
        position_value=position_units * (equity / max(position_units, 1.0)) if position_units else 0.0,
        avg_entry_price=100.0 if position_units else None,
        peak_equity=max(equity, cash),
        drawdown=0.0,
        timestamp=datetime.now(timezone.utc),
    )


def test_performance_monitor_records_experience(tmp_path) -> None:
    experience_path = tmp_path / "experiences.jsonl"
    metrics_path = tmp_path / "metrics.jsonl"

    monitor = PerformanceMonitor(
        experience_repo=FileExperienceRepository(experience_path),
        accumulator=PerformanceAccumulator(),
        metrics_repo=FilePerformanceRepository(metrics_path),
    )

    market = MarketData(symbol="TEST", price=100.0, timestamp=datetime.now(timezone.utc))
    portfolio_before = _portfolio(equity=10_000.0, cash=10_000.0)
    monitor.bind_state({"feature": 1.0})
    monitor.on_tick(market, portfolio_before)

    action = TradeAction(signal=TradeSignal.BUY, notional=1_000.0)
    monitor.on_action(action, action)

    portfolio_after = portfolio_before
    portfolio_after = PortfolioState(
        cash=9_000.0,
        equity=10_020.0,
        position_units=10.0,
        position_value=1_000.0,
        avg_entry_price=100.0,
        peak_equity=10_020.0,
        drawdown=0.0,
        timestamp=datetime.now(timezone.utc),
    )
    result = ExecutionResult(
        action=action,
        status=OrderStatus.ACCEPTED,
        filled_units=10.0,
        notional_value=1_000.0,
        fee_paid=1.0,
        portfolio=portfolio_after,
    )
    monitor.on_execution(result)

    summary = monitor.finalize_period(market.timestamp)
    assert summary is not None
    assert summary.trades == 1
    assert summary.pnl == portfolio_after.equity - portfolio_before.equity

    frame = FileExperienceRepository(experience_path).load()
    assert len(frame) == 1
    assert frame.iloc[0]["action"] == "BUY"

    metrics_text = metrics_path.read_text().strip().splitlines()
    assert len(metrics_text) == 1

