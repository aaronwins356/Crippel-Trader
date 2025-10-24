"""Sentiment scraping utilities."""
from __future__ import annotations

import random
from typing import Iterable


async def fetch_sentiment(topics: Iterable[str]) -> dict[str, float]:
    """Mock sentiment fetcher returning deterministic-ish scores."""

    result: dict[str, float] = {}
    for topic in topics:
        random.seed(topic)
        result[topic] = round(0.2 + random.random() * 0.6, 3)
    return result
