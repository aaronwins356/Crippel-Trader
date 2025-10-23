"""Lightweight Kraken client stubs for trading and market data streaming."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Awaitable, Callable, Dict, Iterable, Optional

import websockets
from websockets import WebSocketClientProtocol

from ...utils.logger import get_child

logger = get_child("kraken")

TickerHandler = Callable[[str, Dict[str, Any]], Awaitable[None] | None]


class KrakenClient:
    def __init__(self, api_key: str | None = None, api_secret: str | None = None) -> None:
        self.api_key = api_key or os.getenv("KRAKEN_API_KEY")
        self.api_secret = api_secret or os.getenv("KRAKEN_API_SECRET")
        self.enabled = bool(self.api_key and self.api_secret)

    async def submit_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        if not order or not order.get("symbol") or not order.get("side"):
            raise ValueError("Invalid order payload for Kraken execution")
        if not order.get("quantity") or not order.get("price"):
            raise ValueError("Invalid order payload for Kraken execution")

        await asyncio.sleep(0)  # make the stub cooperative

        if not self.enabled:
            reference = f"SIM-{int(asyncio.get_running_loop().time() * 1000)}"
            logger.info("Simulated Kraken order", extra={"reference": reference, "order": order})
            return {"reference": reference, "status": "simulated"}

        reference = f"KRAKEN-{int(asyncio.get_running_loop().time() * 1000)}"
        logger.info("Kraken order submitted (stub)", extra={"reference": reference, "order": order})
        return {"reference": reference, "status": "submitted"}


class KrakenMarketDataFeed:
    """Maintain a resilient WebSocket connection to Kraken's public API."""

    URL = "wss://ws.kraken.com"

    def __init__(
        self,
        pairs: Iterable[str],
        handler: Optional[TickerHandler] = None,
        reconnect_delay: float = 5.0,
    ) -> None:
        self.pairs = sorted(set(pairs))
        self.handler = handler
        self.reconnect_delay = float(reconnect_delay)
        self._running = False
        self._websocket: Optional[WebSocketClientProtocol] = None

    async def run(self) -> None:
        if not self.pairs:
            return
        self._running = True
        while self._running:
            try:
                async with websockets.connect(
                    self.URL,
                    ping_interval=20,
                    ping_timeout=20,
                    max_queue=None,
                ) as websocket:
                    self._websocket = websocket
                    await self._subscribe(websocket)
                    async for message in websocket:
                        if not self._running:
                            break
                        payload = json.loads(message)
                        if isinstance(payload, dict):
                            event = payload.get("event")
                            if event == "heartbeat":
                                continue
                            if event == "subscriptionStatus" and payload.get("status") != "subscribed":
                                logger.warning(
                                    "Kraken subscription issue",
                                    extra={"payload": payload},
                                )
                            continue
                        if (
                            isinstance(payload, list)
                            and len(payload) >= 4
                            and payload[-2] == "ticker"
                        ):
                            pair = payload[-1]
                            data = payload[1]
                            await self._dispatch(pair, data)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Kraken WebSocket connection error", exc_info=exc)
                if self._running:
                    await asyncio.sleep(self.reconnect_delay)
            finally:
                self._websocket = None
        self._running = False

    async def stop(self) -> None:
        self._running = False
        if self._websocket and not self._websocket.closed:
            try:
                await self._websocket.close()
            except Exception:  # pragma: no cover - defensive close
                logger.debug("Failed to close Kraken WebSocket cleanly")

    async def _subscribe(self, websocket: WebSocketClientProtocol) -> None:
        subscribe_message = json.dumps(
            {
                "event": "subscribe",
                "pair": self.pairs,
                "subscription": {"name": "ticker"},
            }
        )
        await websocket.send(subscribe_message)

    async def _dispatch(self, pair: str, payload: Dict[str, Any]) -> None:
        if not self.handler:
            return
        try:
            result = self.handler(pair, payload)
            if asyncio.iscoroutine(result):
                await result
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Kraken ticker handler failure", exc_info=exc)


__all__ = ["KrakenClient", "KrakenMarketDataFeed"]
