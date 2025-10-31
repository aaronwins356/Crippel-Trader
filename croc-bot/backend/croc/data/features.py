"""Shared feature engineering utilities for training and live trading."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

import numpy as np

from ..models.types import Tick


@dataclass(slots=True)
class FeaturePipeline:
    """Vectorised feature pipeline using numpy arrays."""

    fast_window: int = 12
    slow_window: int = 26
    vol_window: int = 20

    def transform(self, prices: np.ndarray, volumes: np.ndarray) -> np.ndarray:
        if prices.ndim != 1 or volumes.ndim != 1:
            raise ValueError("prices and volumes must be 1-D arrays")
        if len(prices) != len(volumes):
            raise ValueError("prices and volumes must align")
        if len(prices) < self.slow_window:
            raise ValueError("not enough samples for slow window")

        prev = np.roll(prices, 1)
        prev[0] = prices[0]
        denominator = np.where(prev == 0, 1.0, prev)
        returns = (prices - prev) / denominator
        fast = self._ema(prices, self.fast_window)
        slow = self._ema(prices, self.slow_window)
        vol = self._rolling_std(returns, self.vol_window)
        volume_z = self._zscore(volumes, self.vol_window)
        features = np.vstack((returns, fast - slow, vol, volume_z)).T
        return features

    @staticmethod
    def _ema(series: np.ndarray, window: int) -> np.ndarray:
        alpha = 2 / (window + 1)
        ema = np.zeros_like(series)
        ema[0] = series[0]
        for i in range(1, len(series)):
            ema[i] = alpha * series[i] + (1 - alpha) * ema[i - 1]
        return ema

    @staticmethod
    def _rolling_std(series: np.ndarray, window: int) -> np.ndarray:
        std = np.zeros_like(series)
        for i in range(len(series)):
            start = max(0, i - window + 1)
            std[i] = np.std(series[start : i + 1])
        return std

    @staticmethod
    def _zscore(series: np.ndarray, window: int) -> np.ndarray:
        z = np.zeros_like(series)
        for i in range(len(series)):
            start = max(0, i - window + 1)
            window_slice = series[start : i + 1]
            mean = np.mean(window_slice)
            std = np.std(window_slice) or 1.0
            z[i] = (series[i] - mean) / std
        return z


@dataclass(slots=True)
class LiveFeatureState:
    pipeline: FeaturePipeline
    max_length: int
    prices: list[float] = field(default_factory=list)
    volumes: list[float] = field(default_factory=list)

    def update(self, tick: Tick) -> Optional[np.ndarray]:
        self.prices.append(tick.last)
        self.volumes.append(tick.volume)
        if len(self.prices) > self.max_length:
            self.prices.pop(0)
            self.volumes.pop(0)
        if len(self.prices) < self.pipeline.slow_window:
            return None
        prices = np.array(self.prices, dtype=float)
        volumes = np.array(self.volumes, dtype=float)
        return self.pipeline.transform(prices, volumes)[-1]


def features_from_ticks(ticks: Iterable[Tick], pipeline: Optional[FeaturePipeline] = None) -> np.ndarray:
    pipeline = pipeline or FeaturePipeline()
    prices = np.array([tick.last for tick in ticks], dtype=float)
    volumes = np.array([tick.volume for tick in ticks], dtype=float)
    return pipeline.transform(prices, volumes)


__all__ = ["FeaturePipeline", "LiveFeatureState", "features_from_ticks"]
