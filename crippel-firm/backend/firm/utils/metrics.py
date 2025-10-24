"""Utility helpers for calculating metrics."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class PerformanceLedger:
    """In-memory ledger tracking metrics per bot."""

    metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def record_event(self, bot_id: str, metric: str, value: float) -> None:
        bot_metrics = self.metrics.setdefault(bot_id, {})
        bot_metrics[metric] = bot_metrics.get(metric, 0.0) + value

    def get_bot_summary(self, bot_id: str) -> dict[str, float]:
        return self.metrics.get(bot_id, {}).copy()

    def all_summaries(self) -> dict[str, dict[str, float]]:
        return {bot_id: metrics.copy() for bot_id, metrics in self.metrics.items()}


def calculate_drawdown(equity_curve: list[float]) -> float:
    """Compute the maximum drawdown for the provided equity curve."""
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        drawdown = (peak - equity) / peak if peak else 0.0
        max_drawdown = max(max_drawdown, drawdown)
    return max_drawdown
