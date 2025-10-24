"""Helpers for aggregating performance metrics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..firm.interfaces import MetricDict
from ..firm.scoring import score_bot


@dataclass
class PerformanceScore:
    bot_id: str
    metrics: MetricDict
    total: float


def aggregate_scores(pairs: Iterable[tuple[str, MetricDict]]) -> list[PerformanceScore]:
    scores: list[PerformanceScore] = []
    for bot_id, metrics in pairs:
        components = score_bot(metrics)
        scores.append(PerformanceScore(bot_id=bot_id, metrics=metrics, total=components.total))
    return scores
