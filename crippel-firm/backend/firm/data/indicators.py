"""Market indicator utilities."""
from __future__ import annotations

import math
from datetime import datetime


def relative_strength_index(prices: list[float], period: int = 14) -> float:
    """Compute a simple RSI approximation."""
    if len(prices) < 2:
        return 50.0
    gains = [max(prices[i] - prices[i - 1], 0) for i in range(1, len(prices))]
    losses = [max(prices[i - 1] - prices[i], 0) for i in range(1, len(prices))]
    avg_gain = sum(gains[-period:]) / max(len(gains[-period:]), 1)
    avg_loss = sum(losses[-period:]) / max(len(losses[-period:]), 1)
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def moving_average(prices: list[float], period: int = 10) -> float:
    """Simple moving average."""
    if not prices:
        return 0.0
    return sum(prices[-period:]) / min(len(prices), period)


def market_open_bias(timestamp: datetime) -> float:
    """Return a bias factor based on time of day."""
    hour = timestamp.hour + timestamp.minute / 60
    return math.cos(hour / 24 * math.pi * 2)
