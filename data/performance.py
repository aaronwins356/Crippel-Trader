"""Performance metric tracking for feedback-driven training."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from math import sqrt
from pathlib import Path
from statistics import mean, stdev
from typing import Iterable, Protocol


@dataclass(slots=True)
class PerformanceSummary:
    """Aggregated metrics for a trading period."""

    period_start: datetime
    period_end: datetime
    trades: int
    pnl: float
    sharpe: float
    win_rate: float
    max_drawdown: float
    avg_latency: float

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["period_start"] = self.period_start.isoformat()
        payload["period_end"] = self.period_end.isoformat()
        return payload


class PerformanceRepository(Protocol):
    """Persistence for performance summaries."""

    def append(self, summary: PerformanceSummary) -> None:
        ...


class FilePerformanceRepository:
    """JSONL-backed storage for model evaluation summaries."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, summary: PerformanceSummary) -> None:
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(summary.to_dict()))
            handle.write("\n")


class PerformanceAccumulator:
    """Incrementally maintains portfolio statistics for a period."""

    def __init__(self) -> None:
        self._start: datetime | None = None
        self._end: datetime | None = None
        self._start_equity: float | None = None
        self._peak_equity: float | None = None
        self._equity_curve: list[tuple[datetime, float]] = []
        self._rewards: list[float] = []
        self._latencies: list[float] = []

    def record_equity(self, timestamp: datetime, equity: float) -> None:
        if self._start is None:
            self._start = timestamp
            self._start_equity = equity
            self._peak_equity = equity
        self._end = timestamp
        if self._peak_equity is None or equity > self._peak_equity:
            self._peak_equity = equity
        self._equity_curve.append((timestamp, equity))

    def record_trade(self, reward: float, latency: float | None) -> None:
        self._rewards.append(reward)
        if latency is not None:
            self._latencies.append(latency)

    def _compute_sharpe(self) -> float:
        if not self._rewards or self._start_equity in (None, 0.0):
            return 0.0
        returns: list[float] = []
        equity = float(self._start_equity)
        for reward in self._rewards:
            if equity != 0.0:
                returns.append(reward / equity)
            equity += reward
        if len(returns) < 2:
            return 0.0
        return mean(returns) / stdev(returns) * sqrt(len(returns))

    def _compute_drawdown(self) -> float:
        drawdown = 0.0
        peak = 0.0
        for _, equity in self._equity_curve:
            if equity > peak:
                peak = equity
            if peak > 0:
                drawdown = max(drawdown, (peak - equity) / peak)
        return drawdown

    def _compute_win_rate(self) -> float:
        if not self._rewards:
            return 0.0
        wins = sum(1 for reward in self._rewards if reward > 0)
        return wins / len(self._rewards)

    def _compute_latency(self) -> float:
        if not self._latencies:
            return 0.0
        return mean(self._latencies)

    def summary(self) -> PerformanceSummary | None:
        if self._start is None or self._end is None:
            return None
        return PerformanceSummary(
            period_start=self._start,
            period_end=self._end,
            trades=len(self._rewards),
            pnl=sum(self._rewards),
            sharpe=self._compute_sharpe(),
            win_rate=self._compute_win_rate(),
            max_drawdown=self._compute_drawdown(),
            avg_latency=self._compute_latency(),
        )

    def reset(self) -> None:
        self.__init__()


def summarize_period(accumulator: PerformanceAccumulator) -> PerformanceSummary | None:
    """Helper returning the current period summary without resetting."""

    return accumulator.summary()


__all__ = [
    "PerformanceSummary",
    "PerformanceRepository",
    "FilePerformanceRepository",
    "PerformanceAccumulator",
    "summarize_period",
]

