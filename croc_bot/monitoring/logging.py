"""Structured logging utilities."""
from __future__ import annotations

import logging
from time import perf_counter

import structlog

from ..domain import MarketData, TradeAction
from ..execution.base import ExecutionResult, PortfolioState
from .base import BaseMonitor


def configure_logging(level: int = logging.INFO) -> None:
    """Configure structlog for low-overhead structured logging."""

    logging.basicConfig(level=level)
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level),
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
    )


class StructuredLoggingMonitor(BaseMonitor):
    """Monitor emitting structured logs for each engine event."""

    def __init__(self, name: str = "croc_bot") -> None:
        self._logger = structlog.get_logger(name)
        self._last_tick_time = perf_counter()

    def on_tick(self, market: MarketData, portfolio: PortfolioState) -> None:
        now = perf_counter()
        loop_latency = now - self._last_tick_time
        self._last_tick_time = now
        self._logger.info(
            "market_tick",
            symbol=market.symbol,
            price=market.price,
            timestamp=market.timestamp.isoformat(),
            cash=portfolio.cash,
            equity=portfolio.equity,
            position_units=portfolio.position_units,
            drawdown=portfolio.drawdown,
            loop_latency=loop_latency,
        )

    def on_action(self, raw: TradeAction, adjusted: TradeAction) -> None:
        self._logger.info(
            "strategy_action",
            raw_signal=raw.signal.name,
            raw_notional=raw.notional,
            adjusted_signal=adjusted.signal.name,
            adjusted_notional=adjusted.notional,
            metadata=adjusted.metadata or raw.metadata,
        )

    def on_execution(self, result: ExecutionResult) -> None:
        self._logger.info(
            "execution_result",
            signal=result.action.signal.name,
            status=result.status.name,
            filled_units=result.filled_units,
            notional=result.notional_value,
            fee=result.fee_paid,
            equity=result.portfolio.equity,
            cash=result.portfolio.cash,
        )

    def on_error(self, error: Exception) -> None:  # pragma: no cover - logging hook
        self._logger.exception("engine_error", error=str(error))
