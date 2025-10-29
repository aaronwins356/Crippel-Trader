"""Validation utilities for configuration and trading inputs."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Sequence

import httpx

from utils.kraken import normalize_symbol


@dataclass(frozen=True)
class ValidationError:
    """Represents a single validation error message."""

    field: str
    message: str


_KRAKEN_REST_ENDPOINT = "https://api.kraken.com/0/public/AssetPairs"
_KRAKEN_FALLBACK = {
    "XBT/USD",
    "XBT/EUR",
    "ETH/USD",
    "ETH/EUR",
    "SOL/USD",
    "ADA/USD",
    "XRP/USD",
    "DOT/USD",
    "LTC/USD",
}


@lru_cache(maxsize=1)
def _load_remote_pairs() -> set[str]:
    """Fetch supported Kraken pairs using the public REST endpoint.

    Falls back to a conservative static set if the request fails.
    """

    try:
        response = httpx.get(_KRAKEN_REST_ENDPOINT, timeout=5.0)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return set(_KRAKEN_FALLBACK)

    result = payload.get("result", {})
    discovered: set[str] = set()
    for details in result.values():
        if not isinstance(details, dict):
            continue
        ws_name = details.get("wsname")
        if not isinstance(ws_name, str):
            continue
        discovered.add(normalize_symbol(ws_name))

    return discovered or set(_KRAKEN_FALLBACK)


def validate_symbols(pairs: Iterable[str]) -> tuple[list[str], list[ValidationError]]:
    """Validate and normalise user provided trading symbols.

    Parameters
    ----------
    pairs:
        Iterable of user supplied pair strings (e.g. ``"BTC/USD"``).

    Returns
    -------
    tuple[list[str], list[ValidationError]]
        A tuple of the validated, normalised symbols and any validation errors.
    """

    allowed_pairs = _load_remote_pairs()
    normalized: list[str] = []
    errors: list[ValidationError] = []

    for raw_pair in pairs:
        pair = normalize_symbol(raw_pair)
        if pair not in allowed_pairs:
            errors.append(ValidationError("trading.symbols", f"Unsupported Kraken pair: {raw_pair}"))
            continue
        normalized.append(pair)

    # Ensure symbols are unique to prevent over-allocation of capital across duplicates.
    seen: set[str] = set()
    unique_normalized: list[str] = []
    for pair in normalized:
        if pair in seen:
            errors.append(ValidationError("trading.symbols", f"Duplicate symbol: {pair}"))
            continue
        seen.add(pair)
        unique_normalized.append(pair)

    return unique_normalized, errors


def validate_fee(value: float, field: str) -> list[ValidationError]:
    if value < 0 or value > 0.1:
        return [ValidationError(field, "Fee must be between 0 and 10%.")]
    return []


def validate_positive(value: float, field: str, *, allow_zero: bool = False) -> list[ValidationError]:
    if allow_zero and value == 0:
        return []
    if value <= 0:
        return [ValidationError(field, "Value must be positive.")]
    return []


def validate_bounds(value: float, field: str, min_value: float, max_value: float) -> list[ValidationError]:
    if not (min_value <= value <= max_value):
        return [ValidationError(field, f"Value must be between {min_value} and {max_value}.")]
    return []


def collect_errors(*error_groups: Sequence[ValidationError]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for group in error_groups:
        errors.extend(group)
    return errors
