"""Application settings using pydantic-settings."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FeesSettings(BaseModel):
    maker_bps: float = Field(1.0, description="Maker fee in basis points")
    taker_bps: float = Field(2.5, description="Taker fee in basis points")


class RiskSettings(BaseModel):
    max_total_exposure: float = Field(0.5, description="Max fraction of equity exposed")
    max_symbol_exposure: float = Field(0.3, description="Max fraction per symbol")
    max_drawdown: float = Field(0.15, description="Max peak-to-trough drawdown allowed")
    kill_switch_drawdown: float = Field(0.25, description="Hard stop drawdown threshold")


class HiringSettings(BaseModel):
    eval_interval_sec: float = 10.0
    hire_threshold: float = 0.55
    fire_threshold: float = 0.25
    min_tenure_sec: float = 60.0
    cooldown_sec: float = 30.0
    narrative_path: Path = Path("./data/narratives.log")


class PersistenceSettings(BaseModel):
    database_path: Path = Path("./data/firm.db")
    cache_path: Path = Path("./data/cache")


class ManagerSettings(BaseModel):
    evaluation_window: int = 5
    max_research_bots: int = 3
    max_analyst_bots: int = 2
    max_trader_bots: int = 2
    max_risk_bots: int = 1


class ModeSettings(BaseModel):
    mode: Literal["paper", "live"] = "paper"


class AggressionSettings(BaseModel):
    default: int = Field(4, ge=1, le=10)


class AppSettings(BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(env_prefix="FIRM_", env_nested_delimiter="__", extra="ignore")

    fees: FeesSettings = Field(default_factory=FeesSettings)
    risk: RiskSettings = Field(default_factory=RiskSettings)
    hiring: HiringSettings = Field(default_factory=HiringSettings)
    persistence: PersistenceSettings = Field(default_factory=PersistenceSettings)
    manager: ManagerSettings = Field(default_factory=ManagerSettings)
    mode: ModeSettings = Field(default_factory=ModeSettings)
    aggression: AggressionSettings = Field(default_factory=AggressionSettings)


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached settings instance."""

    return AppSettings()
