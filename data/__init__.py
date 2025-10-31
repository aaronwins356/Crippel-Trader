"""Data ingestion and feature engineering utilities."""

from .experience import ExperienceRepository, FileExperienceRepository, TradeExperience
from .ingestion import (
    BarData,
    FeatureStore,
    InMemoryStream,
    MarketDataSource,
    MarketDataStream,
    RollingFeatureStore,
    compute_returns,
    normalize_quotes,
)
from .performance import (
    FilePerformanceRepository,
    PerformanceAccumulator,
    PerformanceRepository,
    PerformanceSummary,
    summarize_period,
)
from .preprocessing import add_technical_indicators, merge_features

__all__ = [
    "BarData",
    "FeatureStore",
    "InMemoryStream",
    "MarketDataSource",
    "MarketDataStream",
    "RollingFeatureStore",
    "TradeExperience",
    "ExperienceRepository",
    "FileExperienceRepository",
    "PerformanceSummary",
    "PerformanceRepository",
    "FilePerformanceRepository",
    "PerformanceAccumulator",
    "summarize_period",
    "compute_returns",
    "normalize_quotes",
    "add_technical_indicators",
    "merge_features",
]
