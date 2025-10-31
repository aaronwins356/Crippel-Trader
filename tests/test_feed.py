"""Tests for the synthetic data feed."""
from __future__ import annotations

import asyncio

from croc_bot.data_feed import SyntheticFeedConfig, SyntheticPriceFeed


def test_price_feed_deterministic() -> None:
    """Price feed should produce deterministic sequences for the same seed."""

    config = SyntheticFeedConfig(
        symbol="TEST-USD",
        interval_seconds=0,
        initial_price=100.0,
        volatility=0.1,
        seed=7,
    )

    feed_a = SyntheticPriceFeed(config)
    feed_b = SyntheticPriceFeed(config)

    seq_a = [feed_a.read().price for _ in range(5)]
    seq_b = [feed_b.read().price for _ in range(5)]

    assert seq_a == seq_b


def test_price_feed_stream_event_loop() -> None:
    """Asynchronous stream should yield without blocking the event loop."""

    config = SyntheticFeedConfig(
        symbol="TEST-USD",
        interval_seconds=0,
        initial_price=100.0,
        volatility=0.1,
        seed=123,
    )
    feed = SyntheticPriceFeed(config)

    async def collect() -> list[float]:
        prices: list[float] = []
        async for tick in feed.stream():
            prices.append(tick.price)
            if len(prices) == 3:
                break
        return prices

    prices = asyncio.run(collect())
    assert len(prices) == 3
