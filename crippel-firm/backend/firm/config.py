"""Configuration models for the firm."""
from __future__ import annotations

from datetime import timedelta
from typing import Literal

from pydantic import BaseModel, Field


class HiringPolicy(BaseModel):
    """Settings controlling hire/fire behavior."""

    eval_interval_seconds: int = Field(5, ge=1)
    hire_threshold: float = Field(0.65, ge=0, le=1.0)
    fire_threshold: float = Field(0.25, ge=0, le=1.0)
    inactivity_limit: int = Field(5, ge=1)
    max_researchers: int = Field(3, ge=1)
    max_traders: int = Field(2, ge=1)
    max_analysts: int = Field(2, ge=1)
    max_risk_bots: int = Field(1, ge=1)
    supervised_mode: bool = False


class CapitalPolicy(BaseModel):
    """Capital allocation and risk limits."""

    starting_equity: float = Field(100_000.0, ge=0)
    max_drawdown: float = Field(0.2, ge=0, le=1)
    risk_per_trade: float = Field(0.02, ge=0, le=1)
    max_position_usd: float = Field(10_000.0, ge=0)
    rebalance_interval: timedelta = timedelta(seconds=30)


class ResearchSettings(BaseModel):
    """Settings for research bots."""

    openinsider_url: str = "https://www.openinsider.com"
    sentiment_sources: list[str] = ["reddit:wallstreetbets", "rss:cnbc"]
    cache_ttl_seconds: int = 600
    request_timeout: float = 10.0


class ManagerSettings(BaseModel):
    """Manager-specific preferences."""

    narrative_path: str = "manager_narrative.log"
    persistence_path: str = "firm_state.json"
    mode: Literal["autonomous", "supervised"] = "autonomous"


class FirmConfig(BaseModel):
    """Aggregated firm configuration."""

    hiring: HiringPolicy = Field(default_factory=HiringPolicy)
    capital: CapitalPolicy = Field(default_factory=CapitalPolicy)
    research: ResearchSettings = Field(default_factory=ResearchSettings)
    manager: ManagerSettings = Field(default_factory=ManagerSettings)
