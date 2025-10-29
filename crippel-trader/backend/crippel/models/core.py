"""Core domain models."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .enums import Mode, OrderSide, OrderType, SignalType


class PriceTick(BaseModel):
    """A market data update."""

    symbol: str
    price: float = Field(ge=0)
    volume: float = Field(ge=0)
    ts: datetime
    bid: float = Field(default=0.0, ge=0)
    ask: float = Field(default=0.0, ge=0)
    
    @property
    def spread(self) -> float:
        """Calculate bid-ask spread."""
        if self.bid > 0 and self.ask > 0:
            return self.ask - self.bid
        return 0.0
    
    @property
    def mid_price(self) -> float:
        """Calculate mid price between bid and ask."""
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2
        return self.price


class Signal(BaseModel):
    """Strategy signal output."""

    symbol: str
    signal: SignalType
    strength: float = Field(ge=-1.0, le=1.0)
    ts: datetime


class Order(BaseModel):
    """Order submitted to an exchange."""

    id: str
    symbol: str
    side: OrderSide
    type: OrderType
    size: float = Field(gt=0)
    price: float = Field(ge=0)
    ts: datetime
    mode: Mode
    aggression: int = Field(ge=1, le=10)


class Fill(BaseModel):
    """Executed trade fill."""

    order_id: str
    symbol: str
    side: OrderSide
    size: float
    price: float
    fee: float
    ts: datetime
    maker: bool


class Position(BaseModel):
    """Per-symbol position state."""

    symbol: str
    size: float = 0.0
    average_price: float = 0.0
    realized_pnl: float = 0.0

    def update_with_fill(self, fill: Fill) -> None:
        direction = 1.0 if fill.side == OrderSide.BUY else -1.0
        if self.size == 0:
            self.average_price = fill.price
        if direction > 0:
            new_size = self.size + fill.size
            if new_size != 0:
                self.average_price = (
                    (self.size * self.average_price + fill.size * fill.price) / new_size
                )
            self.size = new_size
        else:
            realized = (fill.price - self.average_price) * fill.size
            self.realized_pnl += realized
            self.size -= fill.size
            if abs(self.size) < 1e-9:
                self.size = 0.0
                self.average_price = 0.0


class PortfolioState(BaseModel):
    """Portfolio snapshot."""

    cash: float
    equity: float
    pnl_realized: float
    pnl_unrealized: float
    positions: dict[str, Position]
    mode: Mode
    ts: datetime

    @property
    def total_equity(self) -> float:
        return self.cash + self.pnl_unrealized + self.pnl_realized


class RiskLimits(BaseModel):
    """Risk constraint configuration."""

    per_trade_cap: float
    per_symbol_exposure: float
    drawdown_limit: float


class TradeStat(BaseModel):
    """Aggregated trade statistics."""

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    fees_paid: float = 0.0
    realized_pnl: float = 0.0

    model_config = {"validate_assignment": True, "extra": "ignore"}

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades


class ModeState(BaseModel):
    """Current operating mode."""

    mode: Mode
    live_confirmed: bool


class AggressionParams(BaseModel):
    """Parameters produced by the aggression tuner."""

    aggression: int = Field(ge=1, le=10)
    position_fraction: float
    order_type: OrderType
    stop_distance: float
    take_profit_distance: float
    min_hold_time_s: float
    cooldown_s: float
    signal_threshold: float
    maker_bias: float = Field(ge=0.0, le=1.0)


class BackpressureConfig(BaseModel):
    """WebSocket queue bounds."""

    max_queue: int = Field(default=256, ge=1)
    drop_policy: Literal["oldest", "newest"] = "oldest"
