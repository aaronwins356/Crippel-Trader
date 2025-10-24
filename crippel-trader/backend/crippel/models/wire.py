"""Models exposed on the API boundary."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .core import AggressionParams, PortfolioState, TradeStat
from .enums import Mode, SignalType


class AssetInfo(BaseModel):
    symbol: str
    description: str
    active: bool


class HistoryPoint(BaseModel):
    ts: datetime
    price: float = Field(ge=0)
    volume: float = Field(ge=0)


class OrderRequest(BaseModel):
    symbol: str
    side: str
    size: float = Field(gt=0)
    order_type: str = Field(alias="type")


class SettingsResponse(BaseModel):
    aggression: int
    params: AggressionParams
    mode: Mode


class ModeChangeRequest(BaseModel):
    mode: Mode
    confirm: bool = False


class StatsResponse(BaseModel):
    pnl: float
    win_rate: float
    fees: float
    total_trades: int
    equity: float | None = None
    cash: float | None = None


class StreamMessage(BaseModel):
    channel: str
    payload: dict[str, Any]
    ts: datetime


class SignalMessage(BaseModel):
    symbol: str
    signal: SignalType
    strength: float
    ts: datetime


class PortfolioMessage(BaseModel):
    cash: float
    equity: float
    pnl_realized: float
    pnl_unrealized: float
    total_equity: float
    ts: datetime


class ModeMessage(BaseModel):
    mode: Mode
    live: bool
    ts: datetime


class AggregatedState(BaseModel):
    portfolio: PortfolioState
    stats: TradeStat
    aggression: AggressionParams
