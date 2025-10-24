"""Aggression parameter tuning."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyParams:
    """Parameters derived from aggression level."""

    aggression: int
    size_frac: float
    signal_threshold: float
    cooldown_ms: int
    hold_ms: int
    stop_atr: float
    take_profit_atr: float


def tune_params(aggression: int) -> StrategyParams:
    """Map aggression 1-10 into strategy parameters."""

    aggression = max(1, min(aggression, 10))
    size_frac = 0.02 + (aggression - 1) * 0.01
    signal_threshold = 0.55 - (aggression - 1) * 0.03
    cooldown_ms = int(3000 - (aggression - 1) * 200)
    hold_ms = int(120000 + (aggression - 1) * 15000)
    stop_atr = max(0.5, 1.5 - (aggression - 1) * 0.1)
    take_profit_atr = 1.5 + (aggression - 1) * 0.1
    return StrategyParams(
        aggression=aggression,
        size_frac=size_frac,
        signal_threshold=signal_threshold,
        cooldown_ms=max(500, cooldown_ms),
        hold_ms=hold_ms,
        stop_atr=stop_atr,
        take_profit_atr=take_profit_atr,
    )
