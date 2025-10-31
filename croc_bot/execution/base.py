"""Execution client interfaces and shared models."""
from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto

from ..domain import MarketData, TradeAction


class OrderStatus(Enum):
    """Outcome of an order submission."""

    ACCEPTED = auto()
    REJECTED = auto()
    SKIPPED = auto()


@dataclass(slots=True)
class PortfolioState:
    """Snapshot of account health used for risk checks and strategies."""

    cash: float
    equity: float
    position_units: float
    position_value: float
    avg_entry_price: float | None
    peak_equity: float
    drawdown: float
    timestamp: datetime


@dataclass(slots=True)
class ExecutionResult:
    """Details about an executed or skipped action."""

    action: TradeAction
    status: OrderStatus
    filled_units: float
    notional_value: float
    fee_paid: float
    portfolio: PortfolioState


class ExecutionClient(abc.ABC):
    """Interface for trade execution backends."""

    @abc.abstractmethod
    def update_market(self, market: MarketData) -> PortfolioState:
        """Update valuations for the latest market data."""

    @abc.abstractmethod
    async def execute(self, action: TradeAction, market: MarketData) -> ExecutionResult:
        """Execute a trade action asynchronously."""
