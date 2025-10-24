from __future__ import annotations

from datetime import datetime, timedelta

from crippel.engine.strategy import StrategyEngine
from crippel.models.core import PriceTick
from crippel.models.enums import SignalType


def test_strategy_generates_signals() -> None:
    engine = StrategyEngine(aggression=5)
    base_ts = datetime.utcnow()
    prices = [100, 5000, 5005, 5010]
    signals: list[SignalType] = []
    for idx, price in enumerate(prices):
        tick = PriceTick(symbol="XBT/USD", price=price, volume=1.0, ts=base_ts + timedelta(seconds=idx))
        signal = engine.on_tick(tick)
        signals.append(signal.signal)
    assert SignalType.LONG in signals or SignalType.SHORT in signals
