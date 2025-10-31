"""Metrics aggregation exposed via FastAPI."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from statistics import mean
from typing import Deque

from ..models.types import Fill, Metrics, Tick


@dataclass
class MetricsCollector:
    window: int = 256
    _pnl: float = 0.0
    _wins: int = 0
    _trades: int = 0
    _latencies: Deque[float] = field(default_factory=lambda: deque(maxlen=256))
    _drawdowns: Deque[float] = field(default_factory=lambda: deque(maxlen=256))
    _exposures: Deque[float] = field(default_factory=lambda: deque(maxlen=256))
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def record_fill(self, fill: Fill, position_size: float, drawdown: float, latency_ms: float) -> None:
        async with self._lock:
            pnl = (fill.price * fill.size) if fill.side.value == "sell" else -(fill.price * fill.size)
            self._pnl += pnl - fill.fee
            if pnl > 0:
                self._wins += 1
            self._trades += 1
            self._latencies.append(latency_ms)
            self._drawdowns.append(drawdown)
            self._exposures.append(abs(position_size))

    async def record_tick(self, tick: Tick) -> None:
        return None

    async def snapshot(self) -> Metrics:
        async with self._lock:
            win_rate = (self._wins / self._trades) if self._trades else 0.0
            sharpe = (self._pnl / max(1.0, len(self._latencies))) * 0.01
            latency = mean(self._latencies) if self._latencies else 0.0
            drawdown = max(self._drawdowns) if self._drawdowns else 0.0
            exposure = mean(self._exposures) if self._exposures else 0.0
            return Metrics(
                pnl=self._pnl,
                sharpe=sharpe,
                win_rate=win_rate,
                exposure=exposure,
                drawdown=drawdown,
                latency_ms=latency,
            )


__all__ = ["MetricsCollector"]
