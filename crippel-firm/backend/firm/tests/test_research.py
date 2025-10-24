import asyncio

import pytest

from firm.config import FirmConfig
from firm.data.insider_parser import fetch_recent_trades
from firm.data.sentiment_scraper import fetch_sentiment


@pytest.mark.asyncio
async def test_fetch_recent_trades():
    trades = await fetch_recent_trades(limit=3)
    assert len(list(trades)) == 3


@pytest.mark.asyncio
async def test_fetch_sentiment():
    topics = ["reddit:btc", "rss:cnbc"]
    sentiment = await fetch_sentiment(topics)
    assert set(sentiment.keys()) == set(topics)
