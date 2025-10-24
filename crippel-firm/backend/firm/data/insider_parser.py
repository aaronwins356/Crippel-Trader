"""Fetch and parse insider trading information."""
from __future__ import annotations

from datetime import datetime
from random import random
from typing import Iterable


class InsiderTrade(dict):
    """Typed dict representing a parsed insider trade."""

    ticker: str
    insider: str
    transaction_date: datetime
    value: float
    confidence: float


async def fetch_recent_trades(limit: int = 5) -> Iterable[InsiderTrade]:
    """Mock insider trade fetcher.

    The implementation generates deterministic pseudo data suitable for testing.
    """

    now = datetime.utcnow()
    trades: list[InsiderTrade] = []
    for idx in range(limit):
        trade: InsiderTrade = InsiderTrade(
            ticker=f"TCK{idx}",
            insider=f"Insider {idx}",
            transaction_date=now,
            value=10_000 + idx * 1_000,
            confidence=0.5 + random() * 0.5,
        )
        trades.append(trade)
    return trades
