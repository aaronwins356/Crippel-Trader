"""Configuration models for Croc-Bot."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, PositiveFloat, PositiveInt


class TradingSettings(BaseModel):
    max_steps: PositiveInt = Field(default=1)


class SyntheticFeedSettings(BaseModel):
    type: Literal["synthetic"] = "synthetic"
    symbol: str
    interval_seconds: float = Field(..., ge=0.0)
    initial_price: PositiveFloat
    volatility: float = Field(..., ge=0.0)
    seed: int = Field(..., ge=0)


class MovingAverageStrategySettings(BaseModel):
    type: Literal["moving_average"] = "moving_average"
    fast_window: PositiveInt
    slow_window: PositiveInt
    target_notional: float | None = Field(default=None, gt=0.0)


class RiskSettings(BaseModel):
    type: Literal["simple"] = "simple"
    max_drawdown: float = Field(..., gt=0.0, lt=1.0)
    stop_loss_pct: float = Field(..., gt=0.0, lt=1.0)
    position_size_pct: float = Field(..., gt=0.0, le=1.0)
    max_position_value: PositiveFloat


class SimulationExecutionSettings(BaseModel):
    type: Literal["simulation"] = "simulation"
    starting_balance: PositiveFloat
    trading_fee_bps: int = Field(..., ge=0)


class MonitoringSettings(BaseModel):
    logging_enabled: bool = True
    metrics_enabled: bool = True


class BotConfig(BaseModel):
    trading: TradingSettings
    feed: SyntheticFeedSettings
    strategy: MovingAverageStrategySettings
    risk: RiskSettings
    execution: SimulationExecutionSettings | None = Field(default=None)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)

    model_config = dict(extra="ignore")


def load_config(path: Path) -> BotConfig:
    return BotConfig.model_validate_json(path.read_text(encoding="utf-8"))
