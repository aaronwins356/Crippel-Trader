"""Feature engineering and preprocessing utilities."""
from __future__ import annotations

from typing import Iterable

import pandas as pd


def add_technical_indicators(frame: pd.DataFrame, periods: Iterable[int]) -> pd.DataFrame:
    """Append simple moving averages for each lookback period."""

    enriched = frame.copy()
    for period in periods:
        enriched[f"sma_{period}"] = frame["close"].rolling(window=period, min_periods=period).mean()
    return enriched.dropna()


def merge_features(*frames: pd.DataFrame) -> pd.DataFrame:
    """Align and merge multiple feature matrices."""

    merged = pd.concat(frames, axis=1).sort_index()
    merged = merged.loc[~merged.index.duplicated(keep="last")]
    return merged.dropna()
