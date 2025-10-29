"""Validation utilities for configuration and trading inputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

KRAKEN_PAIRS = {
    "XBT/USD",
    "ETH/USD",
    "ADA/USD",
    "SOL/USD",
    "XRP/USD",
    "DOT/USD",
    "LTC/USD",
    "XBT/EUR",
    "ETH/EUR",
}


@dataclass(frozen=True)
class ValidationError:
    field: str
    message: str


def validate_pairs(pairs: Iterable[str]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for pair in pairs:
        if pair not in KRAKEN_PAIRS:
            errors.append(ValidationError("trading.pairs", f"Unsupported Kraken pair: {pair}"))
    return errors


def validate_fee(value: float, field: str) -> list[ValidationError]:
    if value < 0 or value > 0.1:
        return [ValidationError(field, "Fee must be between 0 and 10%.")]
    return []


def validate_positive(value: float, field: str, allow_zero: bool = False) -> list[ValidationError]:
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
