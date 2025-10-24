"""Simplified Kraken adapter for live trading."""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Literal, Optional

import httpx

from ..logging import get_logger


@dataclass
class KrakenConfig:
    base_url: str = "https://api.kraken.com"
    api_key: str | None = None
    api_secret: str | None = None


class KrakenAdapter:
    """Minimal async adapter to interact with Kraken REST API."""

    def __init__(self, config: KrakenConfig | None = None) -> None:
        cfg = config or KrakenConfig(
            api_key=os.getenv("KRAKEN_API_KEY"),
            api_secret=os.getenv("KRAKEN_API_SECRET"),
        )
        self.config = cfg
        self._client = httpx.AsyncClient(base_url=cfg.base_url, timeout=10.0)
        self._logger = get_logger("kraken")
        self._semaphore = asyncio.Semaphore(3)

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: Literal["GET", "POST"], path: str, data: dict[str, Any] | None = None) -> Any:
        headers: dict[str, str] = {}
        if self.config.api_key:
            headers["API-Key"] = self.config.api_key
        async with self._semaphore:
            response = await self._client.request(method, path, json=data, headers=headers)
            response.raise_for_status()
            return response.json()

    async def buy(self, symbol: str, quantity: float, price: float) -> dict[str, Any]:
        payload = {"pair": symbol, "type": "buy", "volume": quantity, "price": price}
        try:
            data = await self._request("POST", "/0/private/AddOrder", payload)
        except httpx.HTTPError as exc:  # pragma: no cover - network failure
            self._logger.error("kraken_buy_failed", error=str(exc))
            raise
        return {"symbol": symbol, "side": "BUY", "quantity": quantity, "price": price, "data": data}

    async def sell(self, symbol: str, quantity: float, price: float) -> dict[str, Any]:
        payload = {"pair": symbol, "type": "sell", "volume": quantity, "price": price}
        try:
            data = await self._request("POST", "/0/private/AddOrder", payload)
        except httpx.HTTPError as exc:  # pragma: no cover
            self._logger.error("kraken_sell_failed", error=str(exc))
            raise
        return {"symbol": symbol, "side": "SELL", "quantity": quantity, "price": price, "data": data}

    async def balance(self) -> dict[str, Any]:
        try:
            data = await self._request("POST", "/0/private/Balance")
        except httpx.HTTPError as exc:  # pragma: no cover
            self._logger.error("kraken_balance_failed", error=str(exc))
            raise
        return data
