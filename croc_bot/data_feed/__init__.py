"""Market data ingestion components."""
from .base import DataFeed
from .synthetic import SyntheticFeedConfig, SyntheticPriceFeed

__all__ = ["DataFeed", "SyntheticFeedConfig", "SyntheticPriceFeed"]
