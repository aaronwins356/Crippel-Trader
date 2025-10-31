"""Monitors that feed trading experiences back into ML pipelines."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from time import perf_counter
from typing import Mapping, MutableMapping

from data.experience import ExperienceRepository, TradeExperience
from data.performance import (
    PerformanceAccumulator,
    PerformanceRepository,
    PerformanceSummary,
)

from ..domain import MarketData, TradeAction
from ..execution.base import ExecutionResult, PortfolioState
from .base import BaseMonitor


@dataclass(slots=True)
class PerformanceMonitorConfig:
    """Configuration toggles for performance monitoring."""

    experience_limit: int | None = None
    auto_finalize: bool = False


class PerformanceMonitor(BaseMonitor):
    """Captures state-action-reward tuples and aggregates metrics."""

    def __init__(
        self,
        experience_repo: ExperienceRepository,
        accumulator: PerformanceAccumulator,
        *,
        metrics_repo: PerformanceRepository | None = None,
        config: PerformanceMonitorConfig | None = None,
    ) -> None:
        self._experience_repo = experience_repo
        self._accumulator = accumulator
        self._metrics_repo = metrics_repo
        self._config = config or PerformanceMonitorConfig()
        self._last_market: MarketData | None = None
        self._previous_equity: float | None = None
        self._pending_state: dict[str, float] = {}
        self._pending_metadata: MutableMapping[str, object] = {}
        self._last_action: TradeAction | None = None
        self._last_action_time: float | None = None

    def bind_state(self, state: Mapping[str, float]) -> None:
        """Attach the latest model state used for the next decision."""

        self._pending_state = dict(state)

    def on_tick(self, market: MarketData, portfolio: PortfolioState) -> None:
        self._last_market = market
        self._previous_equity = portfolio.equity
        self._accumulator.record_equity(market.timestamp, portfolio.equity)

    def on_action(self, raw: TradeAction, adjusted: TradeAction) -> None:
        self._last_action = adjusted
        self._last_action_time = perf_counter()
        self._pending_metadata = adjusted.metadata or raw.metadata

    def on_execution(self, result: ExecutionResult) -> None:
        if self._last_market is None or self._previous_equity is None:
            return
        reward = result.portfolio.equity - self._previous_equity
        self._previous_equity = result.portfolio.equity
        latency = None
        if self._last_action_time is not None:
            latency = perf_counter() - self._last_action_time
        self._accumulator.record_trade(reward, latency)

        experience = TradeExperience(
            timestamp=self._last_market.timestamp,
            symbol=self._last_market.symbol,
            state=self._pending_state,
            action=result.action.signal.name,
            reward=reward,
            done=False,
            info={
                "notional": result.notional_value,
                "latency": latency or 0.0,
                "status": result.status.name,
                "pnl": result.portfolio.equity,
            },
        )
        self._experience_repo.append([experience])
        self._pending_state = {}
        self._pending_metadata = {}
        self._last_action = None
        if self._config.auto_finalize:
            self.finalize_period(self._last_market.timestamp)

    def finalize_period(self, timestamp: datetime) -> PerformanceSummary | None:
        """Finalize and optionally persist the current period metrics."""

        summary = self._accumulator.summary()
        if summary is None:
            return None
        finalized = PerformanceSummary(
            period_start=summary.period_start,
            period_end=timestamp,
            trades=summary.trades,
            pnl=summary.pnl,
            sharpe=summary.sharpe,
            win_rate=summary.win_rate,
            max_drawdown=summary.max_drawdown,
            avg_latency=summary.avg_latency,
        )
        if self._metrics_repo is not None:
            self._metrics_repo.append(finalized)
        self._accumulator.reset()
        return finalized

    def flush(self) -> None:
        if self._metrics_repo is None:
            return
        summary = self._accumulator.summary()
        if summary:
            self._metrics_repo.append(summary)
            self._accumulator.reset()


__all__ = ["PerformanceMonitor", "PerformanceMonitorConfig"]

