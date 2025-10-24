"""Technical indicator utilities."""
from __future__ import annotations

from collections import deque
from typing import Iterable, Sequence


def ema(values: Sequence[float], period: int) -> float:
    if not values:
        return 0.0
    k = 2 / (period + 1)
    ema_value = values[0]
    for value in values[1:]:
        ema_value = value * k + ema_value * (1 - k)
    return ema_value


def macd(values: Sequence[float]) -> tuple[float, float, float]:
    if len(values) < 26:
        return 0.0, 0.0, 0.0
    ema12 = ema(values, 12)
    ema26 = ema(values, 26)
    macd_line = ema12 - ema26
    signal_line = ema([macd_line] * 9, 9)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def rsi(values: Sequence[float], period: int = 14) -> float:
    if len(values) < period + 1:
        return 50.0
    gains = deque(maxlen=period)
    losses = deque(maxlen=period)
    for prev, current in zip(values[:-1], values[1:]):
        change = current - prev
        if change > 0:
            gains.append(change)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(change))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
