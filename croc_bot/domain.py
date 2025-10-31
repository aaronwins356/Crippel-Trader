"""Shared domain models used across Croc-Bot modules."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any


class TradeSignal(Enum):
    """Enumerates the possible high-level trade intents."""

    BUY = auto()
    SELL = auto()
    HOLD = auto()


@dataclass(slots=True)
class MarketData:
    """Represents a normalized market data snapshot."""

    symbol: str
    price: float
    timestamp: datetime
    raw: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.price <= 0:
            raise ValueError("price must be positive")
        if not self.symbol:
            raise ValueError("symbol must be non-empty")
        if self.timestamp.tzinfo is None:
            # Normalize to UTC to avoid downstream confusion.
            object.__setattr__(self, "timestamp", self.timestamp.replace(tzinfo=timezone.utc))


@dataclass(slots=True)
class TradeAction:
    """Represents a strategy or risk-adjusted decision."""

    signal: TradeSignal
    notional: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_notional(self, notional: float) -> "TradeAction":
        """Return a copy with the provided notional size."""

        if notional < 0:
            raise ValueError("notional must be non-negative")
        updated = dict(self.metadata)
        return TradeAction(signal=self.signal, notional=notional, metadata=updated)


__all__ = ["MarketData", "TradeAction", "TradeSignal"]
