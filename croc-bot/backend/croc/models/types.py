"""Typed domain models used by croc."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from ..config import TradingMode


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class Tick(BaseModel):
    timestamp: datetime
    symbol: str
    bid: float
    ask: float
    last: float
    volume: float

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2


class Order(BaseModel):
    id: str
    symbol: str
    side: Side
    size: float = Field(gt=0)
    price: Optional[float] = Field(default=None, ge=0)
    order_type: OrderType = Field(default=OrderType.MARKET)
    mode: TradingMode = Field(default=TradingMode.PAPER)


class Fill(BaseModel):
    order_id: str
    symbol: str
    side: Side
    size: float
    price: float
    fee: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Position(BaseModel):
    symbol: str
    size: float = 0.0
    avg_price: float = 0.0
    realised_pnl: float = 0.0
    unrealised_pnl: float = 0.0

    def update(self, fill: Fill) -> "Position":
        signed_size = fill.size if fill.side is Side.BUY else -fill.size
        prev_size = self.size
        if prev_size == 0:
            self.size = signed_size
            self.avg_price = fill.price
            return self

        same_direction = prev_size * signed_size > 0
        if same_direction:
            new_size = prev_size + signed_size
            total_notional = self.avg_price * prev_size + fill.price * signed_size
            self.avg_price = total_notional / new_size
            self.size = new_size
            return self

        closed = min(abs(prev_size), abs(signed_size))
        direction = 1 if prev_size > 0 else -1
        pnl = direction * closed * (fill.price - self.avg_price)
        self.realised_pnl += pnl - fill.fee
        new_size = prev_size + signed_size
        self.size = new_size
        if new_size == 0:
            self.avg_price = 0.0
        else:
            self.avg_price = fill.price
        return self


class Metrics(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    pnl: float = 0.0
    sharpe: float = 0.0
    win_rate: float = 0.0
    exposure: float = 0.0
    drawdown: float = 0.0
    latency_ms: float = 0.0


__all__ = ["Tick", "Order", "Fill", "Position", "Metrics", "Side", "OrderType"]
