"""Firm level economics: equity, pnl, performance ledger."""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable

from ..engine.portfolio import Portfolio
from ..settings import FeesSettings, PersistenceSettings, RiskSettings
from ..logging import get_logger


class PerformanceLedger:
    """In-memory metrics store keyed by bot."""

    def __init__(self) -> None:
        self._metrics: Dict[str, Dict[str, float]] = {}

    def record(self, bot_id: str, metric: str, value: float) -> None:
        bucket = self._metrics.setdefault(bot_id, {})
        bucket[metric] = value

    def increment(self, bot_id: str, metric: str, value: float = 1.0) -> None:
        bucket = self._metrics.setdefault(bot_id, {})
        bucket[metric] = bucket.get(metric, 0.0) + value

    def fetch(self, bot_id: str) -> Dict[str, float]:
        return dict(self._metrics.get(bot_id, {}))

    def summary(self) -> Dict[str, Dict[str, float]]:
        return {bot_id: dict(metrics) for bot_id, metrics in self._metrics.items()}


@dataclass
class FirmEconomy:
    """Aggregate state for the firm."""

    fees: FeesSettings
    risk: RiskSettings
    persistence: PersistenceSettings
    ledger: PerformanceLedger = field(default_factory=PerformanceLedger)
    portfolio: Portfolio = field(init=False)
    equity_history: list[tuple[datetime, float]] = field(default_factory=list)
    drawdowns: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._logger = get_logger("economy")
        cache_dir = self.persistence.database_path.parent
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.portfolio = Portfolio(
            maker_fee_bps=self.fees.maker_bps,
            taker_fee_bps=self.fees.taker_bps,
            long_only=True,
        )

    @property
    def realized_pnl(self) -> float:
        return self.portfolio.realized_pnl

    @property
    def unrealized_pnl(self) -> float:
        return self.portfolio.unrealized_pnl

    def update_equity(self, equity: float, ts: datetime | None = None) -> None:
        timestamp = ts or datetime.utcnow()
        self.equity_history.append((timestamp, equity))
        if len(self.equity_history) > 1:
            peak = max(value for _, value in self.equity_history)
            drawdown = (peak - equity) / peak if peak else 0.0
            self.drawdowns.append(drawdown)
        self._logger.debug("Updated equity", equity=equity)

    @property
    def max_drawdown(self) -> float:
        return max(self.drawdowns) if self.drawdowns else 0.0

    def conscience_score(self) -> float:
        profits = self.realized_pnl + self.unrealized_pnl
        risk_penalty = self.max_drawdown * 2.0
        score = profits - risk_penalty
        return score

    def equity_series(self, limit: int = 100) -> list[tuple[datetime, float]]:
        return self.equity_history[-limit:]

    def exposure(self) -> float:
        return self.portfolio.current_exposure_value

    def average_drawdown(self) -> float:
        return statistics.mean(self.drawdowns) if self.drawdowns else 0.0

    def save_snapshot(self, path: Path | None = None) -> None:
        path = path or self.persistence.database_path.with_suffix(".equity.json")
        try:
            import json

            data = [(ts.isoformat(), value) for ts, value in self.equity_history]
            path.write_text(json.dumps(data, indent=2))
        except Exception as exc:  # pragma: no cover
            self._logger.warning("Failed to persist equity history", error=str(exc))
