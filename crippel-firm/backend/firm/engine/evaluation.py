"""Worker evaluation utilities."""
from __future__ import annotations

from typing import Dict

from ..utils.metrics import PerformanceLedger


def score_bot(metrics: dict[str, float]) -> float:
    """Compute a normalized score for a bot based on its metrics."""
    pnl = metrics.get("pnl", 0.0)
    coverage = metrics.get("coverage", 0.0)
    confidence = metrics.get("confidence", 0.0)
    alerts = metrics.get("alerts", 0.0)
    signals = metrics.get("signals", 0.0)
    trades = metrics.get("trades", 0.0)
    positive = pnl / 10_000 + coverage * 0.05 + confidence * 0.5 + signals * 0.1 + trades * 0.05
    penalty = alerts * 0.2
    score = max(min(positive - penalty, 1.0), 0.0)
    return score


def aggregate_scores(ledger: PerformanceLedger) -> Dict[str, float]:
    """Return scores for all bots."""
    scores: Dict[str, float] = {}
    for bot_id, metrics in ledger.all_summaries().items():
        scores[bot_id] = score_bot(metrics)
    return scores
