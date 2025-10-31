"""Reward shaping utilities for trading agents."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RewardWeights:
    lambda_drawdown: float = 0.1
    mu_turnover: float = 0.001


def shaped_reward(pnl: float, drawdown: float, turnover: float, weights: RewardWeights) -> float:
    """Compute shaped reward penalising drawdown and turnover."""

    return pnl - weights.lambda_drawdown * drawdown - weights.mu_turnover * turnover


__all__ = ["RewardWeights", "shaped_reward"]
