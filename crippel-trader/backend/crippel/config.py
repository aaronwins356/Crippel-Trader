"""Application configuration powered by pydantic-settings."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Global application settings."""

    env: Literal["dev", "prod", "test"] = Field(default="dev")
    database_url: str = Field(default="sqlite+aiosqlite:///./crippel.db")
    kraken_api_key: str = Field(default="")
    kraken_api_secret: str = Field(default="")
    live_trading_enabled: bool = Field(default=False)
    default_aggression: int = Field(default=3, ge=1, le=10)
    maker_fee_bps: float = Field(default=2.0, ge=0.0)
    taker_fee_bps: float = Field(default=4.0, ge=0.0)
    tick_interval_ms: int = Field(default=200, ge=10)
    history_window: int = Field(default=256, ge=32)
    drawdown_limit: float = Field(default=0.15, ge=0.0, le=1.0)
    per_trade_cap: float = Field(default=0.2, ge=0.0, le=1.0)
    per_symbol_exposure: float = Field(default=0.5, ge=0.0, le=1.0)

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CRIPPEL_", case_sensitive=False)

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]


@lru_cache
def get_settings() -> AppSettings:
    """Return cached application settings."""
    return AppSettings()
