"""Market data ingestion interfaces and async streaming primitives."""
from __future__ import annotations

import abc
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator, Protocol

import numpy as np
import pandas as pd


class MarketDataSource(Protocol):
    """Protocol describing a pull-based market data source."""

    async def fetch_latest(self) -> pd.DataFrame:
        """Return the most recent batch of market data.

        Implementations should return a DataFrame indexed by timestamp with
        normalized column names (e.g. open, high, low, close, volume).
        """


class MarketDataStream(Protocol):
    """Protocol describing a push-based market data stream."""

    def __aiter__(self) -> AsyncIterator[pd.DataFrame]:
        """Yield normalized market data frames as they arrive."""


@dataclass(slots=True)
class BarData:
    """Typed view of a single OHLCV bar."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    @classmethod
    def from_frame(cls, frame: pd.DataFrame) -> "BarData":
        latest = frame.iloc[-1]
        return cls(
            timestamp=frame.index[-1].to_pydatetime(),
            open=float(latest["open"]),
            high=float(latest["high"]),
            low=float(latest["low"]),
            close=float(latest["close"]),
            volume=float(latest["volume"]),
        )


class InMemoryStream(MarketDataStream):
    """Async iterator wrapping an asyncio.Queue for deterministic testing."""

    def __init__(self, queue: asyncio.Queue[pd.DataFrame]) -> None:
        self._queue = queue

    def __aiter__(self) -> AsyncIterator[pd.DataFrame]:
        return self._consume()

    async def _consume(self) -> AsyncIterator[pd.DataFrame]:
        while True:
            frame = await self._queue.get()
            if frame is None:  # type: ignore[comparison-overlap]
                break
            yield frame


class FeatureStore(abc.ABC):
    """Mutable, vectorized store for engineered features."""

    @abc.abstractmethod
    def update(self, frame: pd.DataFrame) -> None:
        """Update feature cache using the latest market snapshot."""

    @abc.abstractmethod
    def latest(self) -> pd.DataFrame:
        """Return the most recent feature matrix."""


class RollingFeatureStore(FeatureStore):
    """Simple rolling-window feature store built on pandas."""

    def __init__(self, window: int) -> None:
        self._window = window
        self._frames: list[pd.DataFrame] = []

    def update(self, frame: pd.DataFrame) -> None:
        self._frames.append(frame)
        if len(self._frames) > self._window:
            self._frames.pop(0)

    def latest(self) -> pd.DataFrame:
        if not self._frames:
            raise RuntimeError("Feature store is empty")
        return pd.concat(self._frames).tail(self._window)


def normalize_quotes(frame: pd.DataFrame) -> pd.DataFrame:
    """Return quotes with strictly monotonic index and float columns."""

    normalized = frame.sort_index().copy()
    normalized.index = pd.to_datetime(normalized.index, utc=True)
    for column in normalized.columns:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    return normalized.dropna()


def compute_returns(frame: pd.DataFrame, periods: int = 1) -> pd.Series:
    """Vectorized log-returns computation with numerical stability."""

    closes = frame["close"].astype(float)
    shifted = closes.shift(periods)
    returns = np.log(closes / shifted)
    return returns.replace({np.inf: np.nan, -np.inf: np.nan}).dropna()
