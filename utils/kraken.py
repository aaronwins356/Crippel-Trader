"""Kraken utilities for symbol normalisation and precision handling."""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from typing import Dict

_BASE_REMAP: Dict[str, str] = {
    "BTC": "XBT",
    "XBT": "XBT",
    "ETH": "ETH",
    "SOL": "SOL",
    "ADA": "ADA",
    "XRP": "XRP",
    "DOT": "DOT",
    "LTC": "LTC",
}

_QUOTE_PREFERENCES = (
    "USDT",
    "USD",
    "EUR",
    "GBP",
    "BTC",
    "ETH",
)

PRICE_PRECISION = {
    "XBT/USD": Decimal("0.1"),
    "XBT/USDT": Decimal("0.1"),
    "ETH/USD": Decimal("0.01"),
    "ETH/USDT": Decimal("0.01"),
    "ADA/USD": Decimal("0.0001"),
    "SOL/USD": Decimal("0.001"),
    "XRP/USD": Decimal("0.0001"),
    "DOT/USD": Decimal("0.001"),
    "LTC/USD": Decimal("0.01"),
}

SIZE_PRECISION = {
    "XBT/USD": Decimal("0.0001"),
    "XBT/USDT": Decimal("0.0001"),
    "ETH/USD": Decimal("0.001"),
    "ETH/USDT": Decimal("0.001"),
    "ADA/USD": Decimal("1"),
    "SOL/USD": Decimal("0.01"),
    "XRP/USD": Decimal("1"),
    "DOT/USD": Decimal("0.01"),
    "LTC/USD": Decimal("0.001"),
}


def _ensure_symbol_format(raw_symbol: str) -> tuple[str, str]:
    """Return base/quote components inferred from a Kraken style symbol."""

    candidate = raw_symbol.strip().upper().replace("-", "/").replace(":", "/")
    if "/" in candidate:
        base, quote = candidate.split("/", 1)
        return base, quote

    compact = candidate.replace(" ", "")
    for quote in _QUOTE_PREFERENCES:
        if compact.endswith(quote):
            base = compact[: -len(quote)]
            if base:
                return base, quote
    # Fallback: assume a 3/3 split to avoid crashes; Kraken will reject unknown symbols later.
    return compact[:3], compact[3:]


def normalize_symbol(symbol: str) -> str:
    """Normalise a symbol to Kraken's canonical ``BASE/QUOTE`` form."""

    base, quote = _ensure_symbol_format(symbol)
    base = _BASE_REMAP.get(base, base)
    return f"{base}/{quote}"


def kraken_rest_pair(symbol: str) -> str:
    """Convert a ``BASE/QUOTE`` symbol to Kraken's REST format (no slash)."""

    normalized = normalize_symbol(symbol)
    return normalized.replace("/", "")


def kraken_round(value: float, symbol: str, is_size: bool) -> float:
    precision_table = SIZE_PRECISION if is_size else PRICE_PRECISION
    step = precision_table.get(normalize_symbol(symbol))
    if step is None:
        return value
    decimal_value = Decimal(str(value))
    quantized = (decimal_value // step) * step
    return float(quantized.quantize(step, rounding=ROUND_DOWN))
