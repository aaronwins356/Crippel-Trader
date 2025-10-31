"""Append-only CSV storage for observability."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from ..config import StorageConfig
from ..models.types import Fill, Metrics, Tick


class DataStore:
    def __init__(self, config: StorageConfig) -> None:
        self.config = config
        self.config.ticks.mkdir(parents=True, exist_ok=True)
        self.config.trades.mkdir(parents=True, exist_ok=True)
        self.config.metrics.mkdir(parents=True, exist_ok=True)

    def append_tick(self, tick: Tick) -> None:
        path = self.config.ticks / f"{tick.symbol.replace('/', '_')}.csv"
        self._append(
            path,
            ["timestamp", "bid", "ask", "last", "volume"],
            [tick.timestamp.isoformat(), tick.bid, tick.ask, tick.last, tick.volume],
        )

    def append_fill(self, fill: Fill) -> None:
        path = self.config.trades / f"{fill.symbol.replace('/', '_')}.csv"
        self._append(
            path,
            ["timestamp", "order_id", "side", "size", "price", "fee"],
            [
                fill.timestamp.isoformat(),
                fill.order_id,
                fill.side.value,
                fill.size,
                fill.price,
                fill.fee,
            ],
        )

    def append_metrics(self, metrics: Metrics) -> None:
        path = self.config.metrics / "metrics.csv"
        self._append(
            path,
            [
                "timestamp",
                "pnl",
                "sharpe",
                "win_rate",
                "exposure",
                "drawdown",
                "latency_ms",
            ],
            [
                metrics.timestamp.isoformat(),
                metrics.pnl,
                metrics.sharpe,
                metrics.win_rate,
                metrics.exposure,
                metrics.drawdown,
                metrics.latency_ms,
            ],
        )

    def _append(self, path: Path, header: Iterable[str], row: Iterable[object]) -> None:
        is_new = not path.exists()
        with path.open("a", newline="") as fh:
            writer = csv.writer(fh)
            if is_new:
                writer.writerow(header)
            writer.writerow(row)


__all__ = ["DataStore"]
