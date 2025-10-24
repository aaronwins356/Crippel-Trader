"""Performance scoring utilities for worker evaluation."""
from __future__ import annotations

from dataclasses import dataclass

from .interfaces import MetricDict


@dataclass
class ScoreComponents:
    risk_adjusted: float
    hit_rate: float
    latency: float
    policy: float

    @property
    def total(self) -> float:
        return max(0.0, self.risk_adjusted * 0.5 + self.hit_rate * 0.3 + self.latency * 0.1 + self.policy * 0.1)


def _normalize(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    clipped = min(max(value, low), high)
    return (clipped - low) / (high - low)


def score_bot(metrics: MetricDict) -> ScoreComponents:
    """Compute weighted score components for a bot."""

    delta_pnl = metrics.get("delta_realized_pnl", 0.0)
    exposure = metrics.get("avg_exposure", 1.0)
    risk_adjusted = _normalize(delta_pnl / max(exposure, 1e-6), -2.0, 2.0)

    hit_rate = _normalize(metrics.get("hit_rate", 0.5), 0.3, 0.8)

    latency_ms = metrics.get("decision_latency_ms", 200.0)
    latency = 1.0 - _normalize(latency_ms, 50.0, 500.0)

    policy_penalty = metrics.get("policy_adherence", 1.0)
    policy = max(0.0, min(policy_penalty, 1.0))

    return ScoreComponents(risk_adjusted=risk_adjusted, hit_rate=hit_rate, latency=latency, policy=policy)


def summarize_score(metrics: MetricDict) -> float:
    """Convenience helper returning the aggregate score."""

    return score_bot(metrics).total
