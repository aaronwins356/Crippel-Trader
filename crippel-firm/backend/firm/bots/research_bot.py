"""Research bot implementation."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from ..config import ResearchSettings
from ..data.insider_parser import fetch_recent_trades
from ..data.sentiment_scraper import fetch_sentiment
from ..utils.metrics import PerformanceLedger
from .base import WorkerBot


@dataclass
class ResearchConfig:
    settings: ResearchSettings
    refresh_interval: float = 5.0


class ResearchBot(WorkerBot):
    """Generates research insights from insider trades and sentiment."""

    def __init__(
        self,
        event_bus,
        performance_ledger: PerformanceLedger,
        config: ResearchConfig,
    ) -> None:
        super().__init__(event_bus=event_bus, performance_ledger=performance_ledger, bot_type="research")
        self.config = config
        self._ideas: list[dict[str, float]] = []

    async def on_start(self) -> None:
        self.logger.info("ResearchBot %s started", self.bot_id)

    async def on_tick(self) -> None:
        trades = await fetch_recent_trades(limit=5)
        sentiment = await fetch_sentiment(self.config.settings.sentiment_sources)
        ideas: list[dict[str, float]] = []
        for trade in trades:
            confidence = trade["confidence"]
            ticker = trade["ticker"]
            sentiment_score = sentiment.get(f"reddit:{ticker.lower()}", 0.4)
            idea = {"ticker": ticker, "confidence": (confidence + sentiment_score) / 2}
            ideas.append(idea)
        self._ideas = sorted(ideas, key=lambda idea: idea["confidence"], reverse=True)
        await self.publish("research", {"bot_id": self.bot_id, "ideas": self._ideas})
        self.record_metric("coverage", len(self._ideas))
        await asyncio.sleep(self.config.refresh_interval)

    async def on_evaluate(self) -> dict[str, float]:
        coverage = self.performance_ledger.get_bot_summary(self.bot_id).get("coverage", 0)
        avg_conf = sum(idea["confidence"] for idea in self._ideas) / max(len(self._ideas), 1)
        return {"coverage": float(coverage), "confidence": avg_conf}

    async def on_terminate(self) -> None:
        self.logger.info("ResearchBot %s terminated", self.bot_id)
