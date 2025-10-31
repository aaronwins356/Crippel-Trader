"""Prometheus metrics exporter."""
from __future__ import annotations

from time import perf_counter

from prometheus_client import Counter, Histogram

from ..domain import MarketData, TradeAction
from ..execution.base import ExecutionResult, PortfolioState
from .base import BaseMonitor

_LATENCY = Histogram("croc_bot_loop_latency_seconds", "Time between strategy ticks")
_ACTIONS = Counter("croc_bot_actions_total", "Number of actions generated", ["stage"])
_EXECUTIONS = Counter("croc_bot_execution_total", "Number of executions", ["status"])


class MetricsMonitor(BaseMonitor):
    """Record metrics for Prometheus scraping."""

    def __init__(self) -> None:
        self._last_tick = perf_counter()

    def on_tick(self, market: MarketData, portfolio: PortfolioState) -> None:  # noqa: ARG002 - required signature
        now = perf_counter()
        _LATENCY.observe(max(now - self._last_tick, 0.0))
        self._last_tick = now

    def on_action(self, raw: TradeAction, adjusted: TradeAction) -> None:
        _ACTIONS.labels(stage="raw").inc()
        if raw.signal != adjusted.signal or raw.notional != adjusted.notional:
            _ACTIONS.labels(stage="adjusted").inc()

    def on_execution(self, result: ExecutionResult) -> None:
        _EXECUTIONS.labels(status=result.status.name.lower()).inc()
