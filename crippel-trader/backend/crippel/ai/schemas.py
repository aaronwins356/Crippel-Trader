"""Pydantic models describing the assistant's structured outputs."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ResearchItem(BaseModel):
    """Structured representation of an external research datapoint."""

    topic: str
    title: str
    url: str = Field(default="")
    summary: str = Field(default="")
    sentiment: Literal["bullish", "bearish", "neutral"] = "neutral"


class StrategyDirective(BaseModel):
    """Instructions for adjusting the trading strategy."""

    target_aggression: int | None = Field(default=None, ge=1, le=10)
    rationale: str = Field(default="")
    notes: list[str] = Field(default_factory=list)


class TradeRecommendation(BaseModel):
    """Single trade idea produced by the assistant."""

    symbol: str
    action: Literal["buy", "sell", "flat"]
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    size_fraction: float | None = Field(default=None, ge=0.0, le=1.0)
    reasoning: str = Field(default="")


class AssistantDecision(BaseModel):
    """Full response returned by the AI assistant."""

    strategy: StrategyDirective | None = None
    trades: list[TradeRecommendation] = Field(default_factory=list)
    research_summary: str = Field(default="")
    risk_considerations: list[str] = Field(default_factory=list)


__all__ = [
    "AssistantDecision",
    "ResearchItem",
    "StrategyDirective",
    "TradeRecommendation",
]
