"""CCXT based market data feed."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from tenacity import AsyncRetrying, RetryError, stop_after_attempt, wait_exponential

from ..models.types import Tick
from .feed_base import Feed

try:  # pragma: no cover - optional dependency
    import ccxt.async_support as ccxt_async
except ModuleNotFoundError:  # pragma: no cover
    ccxt_async = None


class CCXTFeed(Feed):
    """Thin wrapper around ccxt async ticker polling."""

    def __init__(
        self,
        exchange: str,
        symbol: str,
        *,
        timeframe: str = "1m",
        poll_interval: float = 1.0,
        credentials: Optional[dict[str, str]] = None,
    ) -> None:
        if ccxt_async is None:
            raise RuntimeError("ccxt is not installed; cannot create CCXTFeed")
        super().__init__(symbol)
        self.exchange_id = exchange
        self.timeframe = timeframe
        self.poll_interval = poll_interval
        self.credentials = credentials or {}
        self._client: Optional[ccxt_async.Exchange] = None
        self._stopped = asyncio.Event()

    async def connect(self) -> None:
        klass = getattr(ccxt_async, self.exchange_id)
        self._client = klass({"enableRateLimit": True, **self.credentials})
        self._stopped.clear()

    async def disconnect(self) -> None:
        self._stopped.set()
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def _fetch_ticker(self) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("Feed not connected")
        async for attempt in AsyncRetrying(
            wait=wait_exponential(multiplier=0.5, max=10),
            stop=stop_after_attempt(5),
        ):
            with attempt:
                return await self._client.fetch_ticker(self.symbol)
        raise RuntimeError("Failed to fetch ticker")

    async def _tick_from_payload(self, payload: dict[str, Any]) -> Tick:
        ts = payload.get("timestamp")
        if ts is None:
            timestamp = datetime.now(tz=timezone.utc)
        else:
            timestamp = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        return Tick(
            timestamp=timestamp,
            symbol=self.symbol,
            bid=float(payload.get("bid") or payload.get("last") or 0.0),
            ask=float(payload.get("ask") or payload.get("last") or 0.0),
            last=float(payload.get("last") or 0.0),
            volume=float(payload.get("baseVolume") or payload.get("quoteVolume") or 0.0),
        )

    async def stream(self):  # type: ignore[override]
        if self._client is None:
            raise RuntimeError("Feed not connected")
        while not self._stopped.is_set():
            try:
                payload = await self._fetch_ticker()
            except (RetryError, RuntimeError):
                await asyncio.sleep(self.poll_interval)
                continue
            yield await self._tick_from_payload(payload)
            await asyncio.sleep(self.poll_interval)


__all__ = ["CCXTFeed"]
