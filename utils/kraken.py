"""Kraken utilities for symbol normalization and precision handling."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Dict

SYMBOL_MAP: Dict[str, str] = {
    "BTC/USD": "XBT/USD",
    "BTCUSDT": "XBT/USDT",
    "XBT/USD": "XBT/USD",
    "ETH/USD": "ETH/USD",
    "ETHUSDT": "ETH/USDT",
    "ADA/USD": "ADA/USD",
    "SOL/USD": "SOL/USD",
}

PRICE_PRECISION = {
    "XBT/USD": Decimal("0.1"),
    "ETH/USD": Decimal("0.01"),
    "ADA/USD": Decimal("0.0001"),
    "SOL/USD": Decimal("0.001"),
    "XRP/USD": Decimal("0.0001"),
    "DOT/USD": Decimal("0.001"),
    "LTC/USD": Decimal("0.01"),
}

SIZE_PRECISION = {
    "XBT/USD": Decimal("0.0001"),
    "ETH/USD": Decimal("0.001"),
    "ADA/USD": Decimal("1"),
    "SOL/USD": Decimal("0.01"),
    "XRP/USD": Decimal("1"),
    "DOT/USD": Decimal("0.01"),
    "LTC/USD": Decimal("0.001"),
}


def normalize_symbol(symbol: str) -> str:
    normalized = SYMBOL_MAP.get(symbol.upper(), symbol.upper())
    return normalized


def kraken_round(value: float, symbol: str, is_size: bool) -> float:
    precision_table = SIZE_PRECISION if is_size else PRICE_PRECISION
    step = precision_table.get(symbol)
    if step is None:
        return value
    decimal_value = Decimal(str(value))
    quantized = (decimal_value // step) * step
    return float(quantized.quantize(step, rounding=ROUND_DOWN))
