"""Kraken exchange adapter."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
import websockets
from websockets.client import WebSocketClientProtocol

from ..config import get_settings
from ..logging import get_logger
from ..models.core import Order, PriceTick
from .base import ExchangeAdapter

KRAKEN_WS_URL = "wss://ws.kraken.com"
KRAKEN_REST_URL = "https://api.kraken.com/0/private"


@dataclass
class KrakenAdapter(ExchangeAdapter):
    """Adapter for interacting with Kraken."""

    session: httpx.AsyncClient
    ws: WebSocketClientProtocol | None = None

    def __init__(self) -> None:
        self.session = httpx.AsyncClient(timeout=10)
        self.ws = None
        self._logger = get_logger(__name__)
        self._settings = get_settings()

    async def connect_market_data(self, symbols: list[str]) -> AsyncIterator[PriceTick]:
        await self._ensure_ws()
        if self.ws is None:
            raise RuntimeError("websocket not connected")
        subscribe_msg = json.dumps(
            {
                "event": "subscribe",
                "pair": symbols,
                "subscription": {"name": "ticker"},
            }
        )
        await self.ws.send(subscribe_msg)
        async for message in self.ws:
            if not isinstance(message, str):
                continue
            data = json.loads(message)
            if isinstance(data, dict):
                continue
            if len(data) >= 2 and isinstance(data[1], dict):
                ticker = data[1]
                price = float(ticker.get("c", [0.0])[0])
                volume = float(ticker.get("v", [0.0])[0])
                pair = data[-1]
                yield PriceTick(symbol=pair, price=price, volume=volume, ts=datetime.utcnow())

    async def submit_order(self, order: Order) -> None:
        payload = {
            "pair": order.symbol,
            "type": order.side.value,
            "ordertype": order.type.value,
            "volume": str(order.size),
            "price": str(order.price),
        }
        await self._signed_post("/AddOrder", payload)

    async def _ensure_ws(self) -> None:
        if self.ws and not self.ws.closed:
            return
        self._logger.info("connecting kraken websocket")
        self.ws = await websockets.connect(KRAKEN_WS_URL)

    async def _signed_post(self, path: str, data: dict[str, Any]) -> None:
        if not self._settings.kraken_api_key or not self._settings.kraken_api_secret:
            raise RuntimeError("Kraken API credentials not configured")
        # Placeholder: actual Kraken signing omitted for brevity.
        headers = {"API-Key": self._settings.kraken_api_key}
        await self.session.post(f"{KRAKEN_REST_URL}{path}", data=data, headers=headers)

    async def close(self) -> None:
        if self.ws:
            await self.ws.close()
        await self.session.aclose()
