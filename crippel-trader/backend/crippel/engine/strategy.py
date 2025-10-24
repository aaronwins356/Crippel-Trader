"""Strategy execution pipeline."""
from __future__ import annotations

from collections import defaultdict
from typing import Callable

from ..logging import get_logger
from ..models.core import PriceTick, Signal
from ..models.enums import SignalType
from .params import tune_params
from .prediction import EmaSlopeEstimator


class StrategyEngine:
    """Generate signals based on trend estimation."""

    def __init__(self, aggression: int) -> None:
        self.params = tune_params(aggression)
        self._estimators: dict[str, EmaSlopeEstimator] = defaultdict(lambda: EmaSlopeEstimator.with_span(21))
        self._last_signal: dict[str, Signal] = {}
        self._listeners: list[Callable[[Signal], None]] = []
        self._logger = get_logger(__name__)

    def set_aggression(self, aggression: int) -> None:
        self.params = tune_params(aggression)
        self._logger.info("strategy aggression updated", aggression=aggression)

    def subscribe(self, callback: Callable[[Signal], None]) -> None:
        self._listeners.append(callback)

    def on_tick(self, tick: PriceTick) -> Signal:
        estimator = self._estimators[tick.symbol]
        ema, slope = estimator.update(tick)
        strength = slope / max(ema, 1e-6)
        if strength > self.params.signal_threshold:
            sig_type = SignalType.LONG
        elif strength < -self.params.signal_threshold:
            sig_type = SignalType.SHORT
        else:
            sig_type = SignalType.FLAT
        signal = Signal(symbol=tick.symbol, signal=sig_type, strength=strength, ts=tick.ts)
        self._last_signal[tick.symbol] = signal
        for listener in self._listeners:
            listener(signal)
        return signal

    def last_signal(self, symbol: str) -> Signal | None:
        return self._last_signal.get(symbol)


def build_strategy(aggression: int) -> StrategyEngine:
    return StrategyEngine(aggression)
