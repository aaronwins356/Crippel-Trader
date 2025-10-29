"""Shared state models for Croc-Bot."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class Position:
    symbol: str
    size: float
    avg_price: float
    unrealized_pnl: float = 0.0


@dataclass
class Trade:
    timestamp: datetime
    symbol: str
    side: str
    size: float
    price: float
    fee: float
    total_cost: float
    capital_used: float
    stop_loss: float
    taker: bool
    mode: str

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "side": self.side,
            "size": self.size,
            "price": self.price,
            "fee": self.fee,
            "total_cost": self.total_cost,
            "capital_used": self.capital_used,
            "stop_loss": self.stop_loss,
            "taker": self.taker,
            "mode": self.mode,
        }


@dataclass
class BotState:
    balance: float
    positions: Dict[str, Position] = field(default_factory=dict)
    trades: List[Trade] = field(default_factory=list)
    open_orders: List[dict] = field(default_factory=list)
    daily_realized_pnl: float = 0.0
    total_fees_paid: float = 0.0
    deployed_capital: float = 0.0

    def snapshot(self) -> dict:
        return {
            "balance": self.balance,
            "positions": [vars(pos) for pos in self.positions.values()],
            "trades": [trade.to_dict() for trade in self.trades[-100:]],
            "open_orders": self.open_orders,
            "daily_realized_pnl": self.daily_realized_pnl,
            "total_fees_paid": self.total_fees_paid,
            "deployed_capital": self.deployed_capital,
        }
