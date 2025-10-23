"""Tests for the MACD/RSI strategy behaviour."""

from __future__ import annotations

from datetime import datetime, timedelta
import math

from pybackend.services.portfolio import PortfolioService
from pybackend.services.strategy import StrategyService
from pybackend.utils.indicators import calculate_ema, calculate_macd, calculate_rsi


def build_candles(prices):
    now = datetime.utcnow()
    candles = []
    for index, price in enumerate(prices):
        timestamp = (now - timedelta(minutes=len(prices) - index)).isoformat()
        candles.append(
            {
                "timestamp": timestamp,
                "open": price - 0.5,
                "high": price + 0.5,
                "low": price - 1,
                "close": price,
                "volume": 100 + index,
            }
        )
    return candles


BULLISH_PRICES = [150 + idx * 0.05 + math.sin(idx / 3) * 3 for idx in range(80)]
BEARISH_PRICES = [190 - idx * 0.08 + math.sin(idx / 4) * 0.6 for idx in range(80)]


def open_long(strategy: StrategyService):
    return strategy.process("TEST", build_candles(BULLISH_PRICES), {"sector": "Synthetic"})


def test_opens_long_positions_on_signals():
    portfolio = PortfolioService(100_000)
    strategy = StrategyService(portfolio)
    metrics = {
        "rsi": calculate_rsi(BULLISH_PRICES, 14),
        "ema_fast": calculate_ema(BULLISH_PRICES, 21),
        "macd": calculate_macd(BULLISH_PRICES, 12, 26, 9),
        "price": BULLISH_PRICES[-1],
    }
    if metrics["rsi"] is not None:
        assert metrics["rsi"] <= 80
    if metrics["ema_fast"] is not None:
        assert metrics["price"] >= metrics["ema_fast"] * 0.95
    if metrics["macd"] is not None:
        assert metrics["macd"]["histogram"] >= -0.5
    trade = open_long(strategy)
    assert trade is not None
    assert portfolio.positions["TEST"]["quantity"] > 0


def test_exits_positions_on_reversal():
    portfolio = PortfolioService(100_000)
    strategy = StrategyService(portfolio)
    opening_trade = open_long(strategy)
    assert opening_trade is not None
    pre_quantity = portfolio.positions["TEST"]["quantity"]
    metrics = {
        "rsi": calculate_rsi(BEARISH_PRICES, 14),
        "ema_fast": calculate_ema(BEARISH_PRICES, 21),
        "macd": calculate_macd(BEARISH_PRICES, 12, 26, 9),
        "price": BEARISH_PRICES[-1],
    }
    assert metrics["rsi"] is None or metrics["rsi"] >= 40
    if metrics["ema_fast"] is not None:
        assert metrics["price"] <= metrics["ema_fast"] * 1.05
    if metrics["macd"] is not None:
        assert metrics["macd"]["histogram"] <= 0.1
    exit_trade = strategy.process("TEST", build_candles(BEARISH_PRICES), {"sector": "Synthetic"})
    assert exit_trade is not None
    assert exit_trade["quantity"] < 0
    position = portfolio.positions.get("TEST")
    assert (position["quantity"] if position else 0) <= pre_quantity
