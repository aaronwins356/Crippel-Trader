"""Tests for feed module."""
from __future__ import annotations

from itertools import islice

from core.feed import FeedConfig, PriceFeed


def test_price_feed_deterministic() -> None:
    """Price feed should produce deterministic sequences for the same seed."""

    config = FeedConfig(
        symbol="TEST-USD",
        interval_seconds=1,
        initial_price=100.0,
        volatility=0.1,
        seed=7,
    )

    feed_a = PriceFeed(config)
    feed_b = PriceFeed(config)

    seq_a = [tick.price for tick in islice(feed_a.stream(), 5)]
    seq_b = [tick.price for tick in islice(feed_b.stream(), 5)]

    assert seq_a == seq_b
