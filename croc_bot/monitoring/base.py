"""Base monitor abstractions."""
from __future__ import annotations

import abc
from typing import Iterable

from ..domain import MarketData, TradeAction
from ..execution.base import ExecutionResult, PortfolioState


class BaseMonitor(abc.ABC):
    """Observability hook for engine events."""

    def on_tick(self, market: MarketData, portfolio: PortfolioState) -> None:
        """Called after each market data update."""

    def on_action(self, raw: TradeAction, adjusted: TradeAction) -> None:
        """Called when a strategy decision is evaluated."""

    def on_execution(self, result: ExecutionResult) -> None:
        """Called after an order execution attempt."""

    def on_error(self, error: Exception) -> None:  # pragma: no cover - defensive hook
        """Called if the engine raises an exception."""

    def flush(self) -> None:
        """Flush buffered state if necessary."""


class NoOpMonitor(BaseMonitor):
    """Monitor that ignores all events."""


class CompositeMonitor(BaseMonitor):
    """Fan-out monitor dispatching events to multiple observers."""

    def __init__(self, monitors: Iterable[BaseMonitor]) -> None:
        self._monitors = tuple(monitors)

    def on_tick(self, market: MarketData, portfolio: PortfolioState) -> None:
        for monitor in self._monitors:
            monitor.on_tick(market, portfolio)

    def on_action(self, raw: TradeAction, adjusted: TradeAction) -> None:
        for monitor in self._monitors:
            monitor.on_action(raw, adjusted)

    def on_execution(self, result: ExecutionResult) -> None:
        for monitor in self._monitors:
            monitor.on_execution(result)

    def on_error(self, error: Exception) -> None:  # pragma: no cover - pass-through
        for monitor in self._monitors:
            monitor.on_error(error)

    def flush(self) -> None:
        for monitor in self._monitors:
            monitor.flush()
