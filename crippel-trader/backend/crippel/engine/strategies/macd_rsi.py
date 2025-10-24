"""Reference strategy combining MACD and RSI approximations."""
from __future__ import annotations

from dataclasses import dataclass

from ..prediction import EmaSlopeEstimator
from ...models.core import PriceTick, Signal
from ...models.enums import SignalType


@dataclass
class MacdRsiStrategy:
    fast: EmaSlopeEstimator
    slow: EmaSlopeEstimator
    signal: EmaSlopeEstimator

    def __init__(self, fast_span: float = 12.0, slow_span: float = 26.0, signal_span: float = 9.0) -> None:
        self.fast = EmaSlopeEstimator.with_span(fast_span)
        self.slow = EmaSlopeEstimator.with_span(slow_span)
        self.signal = EmaSlopeEstimator.with_span(signal_span)

    def on_tick(self, tick: PriceTick) -> Signal:
        fast_value, _ = self.fast.update(tick)
        slow_value, _ = self.slow.update(tick)
        macd = fast_value - slow_value
        signal_value, _ = self.signal.update(PriceTick(symbol=tick.symbol, price=macd, volume=tick.volume, ts=tick.ts))
        histogram = macd - signal_value
        if histogram > 0:
            sig = SignalType.LONG
        elif histogram < 0:
            sig = SignalType.SHORT
        else:
            sig = SignalType.FLAT
        return Signal(symbol=tick.symbol, signal=sig, strength=histogram, ts=tick.ts)
