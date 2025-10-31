"""Metrics aggregation exposed via FastAPI."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from statistics import mean
from typing import Deque, List, Tuple

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
    _loop_latencies: Deque[float] = field(default_factory=lambda: deque(maxlen=512))
    _inference_latencies: Deque[float] = field(default_factory=lambda: deque(maxlen=512))
    _error_timestamps: Deque[datetime] = field(default_factory=lambda: deque(maxlen=512))
    _loop_iterations: int = 0
    _pnl_series: Deque[Tuple[datetime, float]] = field(default_factory=lambda: deque(maxlen=2048))
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
            self._inference_latencies.append(latency_ms)
            now = fill.timestamp
            self._pnl_series.append((now, self._pnl))

    async def record_tick(self, tick: Tick) -> None:
        return None

    async def record_loop_iteration(self, duration_ms: float) -> None:
        async with self._lock:
            self._loop_iterations += 1
            self._loop_latencies.append(duration_ms)

    async def record_error(self) -> None:
        async with self._lock:
            self._error_timestamps.append(datetime.utcnow())

    async def snapshot(self) -> Metrics:
        async with self._lock:
            win_rate = (self._wins / self._trades) if self._trades else 0.0
            sharpe = (self._pnl / max(1.0, len(self._latencies))) * 0.01
            latency = mean(self._latencies) if self._latencies else 0.0
            drawdown = max(self._drawdowns) if self._drawdowns else 0.0
            exposure = mean(self._exposures) if self._exposures else 0.0
            loop_p99 = _p99(self._loop_latencies)
            inference_p99 = _p99(self._inference_latencies)
            now = datetime.utcnow()
            error_rate = _error_rate(self._error_timestamps, self._loop_iterations, now)
            pnl_1h = _delta_over(self._pnl_series, timedelta(hours=1), now)
            pnl_1d = _delta_over(self._pnl_series, timedelta(days=1), now)
            drawdown_1d = _drawdown_over(self._pnl_series, timedelta(days=1), now)
            return Metrics(
                pnl=self._pnl,
                sharpe=sharpe,
                win_rate=win_rate,
                exposure=exposure,
                drawdown=drawdown,
                latency_ms=latency,
                loop_p99_ms=loop_p99,
                inference_p99_ms=inference_p99,
                error_rate=error_rate,
                pnl_1h=pnl_1h,
                pnl_1d=pnl_1d,
                drawdown_1d=drawdown_1d,
            )

    async def rollup(self) -> dict[str, float]:
        snapshot = await self.snapshot()
        return snapshot.model_dump()


__all__ = ["MetricsCollector"]


def _p99(values: Deque[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = max(0, int(len(sorted_values) * 0.99) - 1)
    return float(sorted_values[index])


def _error_rate(errors: Deque[datetime], iterations: int, now: datetime) -> float:
    while errors and now - errors[0] > timedelta(hours=1):
        errors.popleft()
    if iterations == 0:
        return 0.0
    return len(errors) / iterations


def _delta_over(series: Deque[Tuple[datetime, float]], window: timedelta, now: datetime) -> float:
    if not series:
        return 0.0
    cutoff = now - window
    baseline = None
    for timestamp, value in reversed(series):
        if timestamp >= cutoff:
            baseline = value
        else:
            break
    if baseline is None:
        baseline = series[0][1]
    return series[-1][1] - baseline


def _drawdown_over(series: Deque[Tuple[datetime, float]], window: timedelta, now: datetime) -> float:
    if not series:
        return 0.0
    cutoff = now - window
    values: List[float] = [value for ts, value in series if ts >= cutoff]
    if not values:
        values = [series[-1][1]]
    peak = values[0]
    max_dd = 0.0
    for value in values:
        peak = max(peak, value)
        max_dd = max(max_dd, peak - value)
    return max_dd
