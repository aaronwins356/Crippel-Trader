"""Technical indicator helpers mirroring the former Node implementation."""

from __future__ import annotations

from math import sqrt
from typing import Iterable, List, Optional


def _to_fixed(value: float, precision: int = 6) -> float:
    """Return ``value`` rounded to ``precision`` decimal places as a float."""

    return float(f"{value:.{precision}f}")


def calculate_sma(values: Iterable[float], period: int) -> Optional[float]:
    values = list(values)
    if len(values) < period:
        return None
    window = values[-period:]
    return _to_fixed(sum(window) / period, 4)


def calculate_ema(values: Iterable[float], period: int) -> Optional[float]:
    values = list(values)
    if len(values) < period:
        return None
    ema = values[-period]
    multiplier = 2 / (period + 1)
    for price in values[-period + 1 :]:
        ema = (price - ema) * multiplier + ema
    return _to_fixed(ema, 4)


def calculate_rsi(values: Iterable[float], period: int = 14) -> Optional[float]:
    values = list(values)
    if len(values) < period + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(len(values) - period + 1, len(values)):
        change = values[i] - values[i - 1]
        if change >= 0:
            gains += change
        else:
            losses -= change
    if losses == 0:
        return 100.0
    rs = gains / losses
    return _to_fixed(100 - 100 / (1 + rs), 2)


def calculate_macd(
    values: Iterable[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> Optional[dict]:
    values = list(values)
    if len(values) < slow + signal:
        return None
    ema_fast_values: List[float] = []
    ema_slow_values: List[float] = []
    ema_fast = values[0]
    ema_slow = values[0]
    k_fast = 2 / (fast + 1)
    k_slow = 2 / (slow + 1)
    for price in values:
        ema_fast = price * k_fast + ema_fast * (1 - k_fast)
        ema_slow = price * k_slow + ema_slow * (1 - k_slow)
        ema_fast_values.append(ema_fast)
        ema_slow_values.append(ema_slow)
    macd_line = [f - s for f, s in zip(ema_fast_values, ema_slow_values)]
    signal_line = macd_line[slow - 1]
    signal_values: List[float] = []
    k_signal = 2 / (signal + 1)
    for i in range(slow, len(macd_line)):
        signal_line = macd_line[i] * k_signal + signal_line * (1 - k_signal)
        signal_values.append(signal_line)
    histogram = [
        macd_line[-len(signal_values) + idx] - value
        for idx, value in enumerate(signal_values)
    ]
    return {
        "macd": _to_fixed(macd_line[-1], 4),
        "signal": _to_fixed(signal_values[-1], 4),
        "histogram": _to_fixed(histogram[-1], 4),
    }


def calculate_volatility(values: Iterable[float], period: int = 30) -> Optional[float]:
    values = list(values)
    if len(values) < period:
        return None
    window = values[-period:]
    avg = sum(window) / period
    variance = sum((value - avg) ** 2 for value in window) / period
    return _to_fixed(sqrt(variance), 4)


def calculate_bollinger_bands(
    values: Iterable[float], period: int = 20, multiplier: float = 2
) -> Optional[dict]:
    values = list(values)
    if len(values) < period:
        return None
    window = values[-period:]
    avg = sum(window) / period
    variance = sum((value - avg) ** 2 for value in window) / period
    std_dev = sqrt(variance)
    return {
        "upper": _to_fixed(avg + multiplier * std_dev, 4),
        "middle": _to_fixed(avg, 4),
        "lower": _to_fixed(avg - multiplier * std_dev, 4),
    }


def calculate_drawdown(values: Iterable[float]) -> float:
    values = list(values)
    if not values:
        return 0.0
    peak = values[0]
    max_drawdown = 0.0
    for value in values:
        if value > peak:
            peak = value
        if peak:
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    return _to_fixed(max_drawdown * 100, 2)


def normalize_number(value: Optional[float], digits: int = 2) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(f"{float(value):.{digits}f}")
    except (TypeError, ValueError):
        return None


__all__ = [
    "calculate_sma",
    "calculate_ema",
    "calculate_rsi",
    "calculate_macd",
    "calculate_volatility",
    "calculate_bollinger_bands",
    "calculate_drawdown",
    "normalize_number",
]
