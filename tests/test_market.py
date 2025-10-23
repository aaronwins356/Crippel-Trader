"""Unit tests for the market data generator."""

from __future__ import annotations

from pybackend.services.market_data import MarketDataService


def test_produces_analytics_with_indicators():
    service = MarketDataService(interval_ms=3_600_000)
    service.tick()
    analytics = service.get_analytics()
    assert len(analytics["assets"]) > 0
    asset = analytics["assets"][0]
    assert asset["rsi"] is None or asset["rsi"] >= 0
    assert asset["macd"] is None or "macd" in asset["macd"]


def test_maintains_history():
    service = MarketDataService(interval_ms=3_600_000)
    service.tick()
    symbol = service.assets[0]["symbol"]
    history = service.get_history(symbol)
    assert len(history) > 0
    candle = history[0]
    assert {"open", "close", "high", "low"}.issubset(candle.keys())
