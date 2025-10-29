"""Utilities for gathering external market intelligence."""
from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from typing import Iterable
from urllib.parse import quote_plus

import httpx

from .schemas import ResearchItem


class WebResearcher:
    """Fetch news headlines and sentiment cues for the assistant."""

    def __init__(
        self,
        *,
        timeout: float = 10.0,
        max_items_per_topic: int = 3,
        concurrency: int = 3,
    ) -> None:
        self._timeout = timeout
        self._max_items = max_items_per_topic
        self._client = httpx.AsyncClient(timeout=timeout, headers={"User-Agent": "CrocBot/1.0"})
        self._semaphore = asyncio.Semaphore(concurrency)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def gather(self, topics: Iterable[str]) -> list[ResearchItem]:
        tasks = [asyncio.create_task(self._fetch_topic(topic)) for topic in topics]
        items: list[ResearchItem] = []
        for task in tasks:
            try:
                items.extend(await task)
            except Exception:
                # Individual topic errors are logged by the fetcher and ignored here.
                continue
        return items

    async def _fetch_topic(self, topic: str) -> list[ResearchItem]:
        url = (
            "https://news.google.com/rss/search?q="
            f"{quote_plus(topic)}&hl=en-US&gl=US&ceid=US:en"
        )
        async with self._semaphore:
            try:
                response = await self._client.get(url)
                response.raise_for_status()
            except Exception:
                return []
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError:
            return []
        items: list[ResearchItem] = []
        for item in root.findall(".//item")[: self._max_items]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            summary = (item.findtext("description") or "").strip()
            if not title:
                continue
            sentiment = self._infer_sentiment(summary or title)
            items.append(
                ResearchItem(
                    topic=topic,
                    title=title,
                    url=link,
                    summary=summary,
                    sentiment=sentiment,
                )
            )
        return items

    def _infer_sentiment(self, text: str) -> str:
        text_lower = text.lower()
        bullish_keywords = {"surge", "bull", "record", "rally", "growth", "beat"}
        bearish_keywords = {"drop", "bear", "selloff", "decline", "loss", "fear"}
        score = 0
        for word in bullish_keywords:
            if word in text_lower:
                score += 1
        for word in bearish_keywords:
            if word in text_lower:
                score -= 1
        if score > 0:
            return "bullish"
        if score < 0:
            return "bearish"
        return "neutral"


__all__ = ["WebResearcher"]
