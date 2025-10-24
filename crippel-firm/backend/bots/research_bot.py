"""Research bot crawling openinsider for ideas."""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

import httpx
from bs4 import BeautifulSoup

from ..firm.economy import PerformanceLedger
from ..settings import PersistenceSettings
from ..logging import get_logger
from .base import WorkerBot


@dataclass
class ResearchConfig:
    refresh_interval: float = 120.0
    base_url: str = "https://www.openinsider.com/screener?s=&o=&pl=&ph=&ll=&lh=&fd=30&fdr=&td=0&fsa=1&fst=0&ss=0&sc=1&ins=on&sic_min=&sic_max=&tmin=&tmax=&vmin=&vmax=&tdir=I"
    cache_path: Path = Path("./data/cache/research")
    min_confidence: float = 0.35
    max_ideas: int = 10
    cache_ttl: float = 60 * 30  # 30 minutes


class ResearchBot(WorkerBot):
    bot_type = "research"

    def __init__(
        self,
        event_bus,
        ledger: PerformanceLedger,
        persistence: PersistenceSettings,
        config: ResearchConfig | None = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        super().__init__(event_bus=event_bus, ledger=ledger)
        self.config = config or ResearchConfig(cache_path=persistence.cache_path / "research")
        self.config.cache_path.mkdir(parents=True, exist_ok=True)
        self._client = client or httpx.AsyncClient(headers={"User-Agent": "CrippelFirmBot/1.0"})
        self._owns_client = client is None
        self._ideas: list[dict[str, Any]] = []
        self._logger = get_logger("bot.research", bot_id=self.bot_id)
        self._last_fetch = 0.0

    async def on_tick(self) -> None:
        now = time.time()
        if now - self._last_fetch < self.config.refresh_interval:
            await asyncio.sleep(self.config.refresh_interval - (now - self._last_fetch))
        ideas = await self._load_ideas()
        if ideas:
            self._ideas = ideas
            payload = {"bot_id": self.bot_id, "ideas": ideas, "ts": time.time()}
            await self.publish("research:idea", payload)
            self.record_metric("coverage", len(ideas))
            self.record_metric("last_confidence", sum(idea["confidence"] for idea in ideas) / len(ideas))
        self._last_fetch = time.time()
        await asyncio.sleep(0.1)

    async def _load_ideas(self) -> list[dict[str, Any]]:
        cache_key = hashlib.sha1(self.config.base_url.encode()).hexdigest()
        cache_file = self.config.cache_path / f"{cache_key}.json"
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < self.config.cache_ttl:
                try:
                    data = json.loads(cache_file.read_text())
                    return data
                except json.JSONDecodeError:
                    cache_file.unlink(missing_ok=True)
        try:
            response = await self._client.get(self.config.base_url)
            response.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - network failure
            self._logger.error("fetch_failed", error=str(exc))
            return self._ideas
        ideas = self._parse_openinsider(response.text)
        cache_file.write_text(json.dumps(ideas, indent=2))
        return ideas

    def _parse_openinsider(self, html: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", {"class": "tinytable"})
        if not table:
            return []
        ideas: list[dict[str, Any]] = []
        rows = table.find_all("tr")
        for row in rows[1:]:
            cells = [cell.get_text(strip=True) for cell in row.find_all("td")]
            if len(cells) < 11:
                continue
            ticker = cells[2]
            insider_role = cells[4]
            price = self._parse_float(cells[6].replace("$", ""))
            qty = self._parse_float(cells[7].replace(",", ""))
            value = self._parse_float(cells[9].replace("$", "").replace(",", ""))
            abnormality = self._parse_float(cells[10].replace("%", ""))
            if value <= 0 or price <= 0:
                continue
            confidence = self._confidence(value=value, abnormality=abnormality)
            if confidence < self.config.min_confidence:
                continue
            idea = {
                "ticker": ticker,
                "role": insider_role,
                "price": price,
                "quantity": qty,
                "value": value,
                "abnormality": abnormality,
                "confidence": round(confidence, 3),
            }
            ideas.append(idea)
        ideas.sort(key=lambda idea: idea["confidence"], reverse=True)
        return ideas[: self.config.max_ideas]

    def _confidence(self, value: float, abnormality: float) -> float:
        size_factor = min(1.0, value / 1_000_000)
        abnormality_factor = min(1.0, abs(abnormality) / 50)
        return 0.2 + 0.6 * size_factor + 0.2 * abnormality_factor

    @staticmethod
    def _parse_float(value: str) -> float:
        try:
            return float(value)
        except ValueError:
            return 0.0

    async def on_evaluate(self) -> dict[str, float]:
        coverage = float(len(self._ideas))
        avg_conf = sum(idea["confidence"] for idea in self._ideas) / coverage if coverage else 0.0
        metrics = {
            "coverage": coverage,
            "avg_confidence": avg_conf,
            "policy_adherence": 1.0,
            "decision_latency_ms": self.config.refresh_interval * 1000,
        }
        return metrics

    async def on_terminate(self) -> None:
        if self._owns_client:
            await self._client.aclose()
