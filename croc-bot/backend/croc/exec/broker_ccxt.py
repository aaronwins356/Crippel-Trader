"""Live broker wrapper guarded behind credentials."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

from ..models.types import Fill, Order
from .broker_base import Broker

try:  # pragma: no cover - optional
    import ccxt.async_support as ccxt_async
except ModuleNotFoundError:  # pragma: no cover
    ccxt_async = None


class CCXTBroker(Broker):
    def __init__(self, exchange: str, *, credentials: dict[str, str]) -> None:
        if ccxt_async is None:
            raise RuntimeError("ccxt not installed")
        if not credentials.get("apiKey") or not credentials.get("secret"):
            raise RuntimeError("Credentials required for live trading")
        self.exchange_id = exchange
        self.credentials = credentials
        self._client: Optional[ccxt_async.Exchange] = None

    async def connect(self) -> None:
        klass = getattr(ccxt_async, self.exchange_id)
        self._client = klass({"enableRateLimit": True, **self.credentials})

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def submit(self, order: Order) -> Fill:
        if self._client is None:
            raise RuntimeError("Broker not connected")
        side = order.side.value
        type_ = order.order_type.value
        params = {"type": type_, "side": side, "symbol": order.symbol, "amount": order.size}
        if order.price is not None:
            params["price"] = order.price
        async for attempt in AsyncRetrying(
            wait=wait_exponential(multiplier=0.5, max=10),
            stop=stop_after_attempt(3),
        ):
            with attempt:
                response = await self._client.create_order(**params)
        price = float(response.get("price") or order.price or 0.0)
        amount = float(response.get("amount") or order.size)
        fee_info = response.get("fee") or {}
        cost = float(fee_info.get("cost") or 0.0)
        return Fill(
            order_id=str(response.get("id")),
            symbol=order.symbol,
            side=order.side,
            size=amount,
            price=price,
            fee=cost,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def cancel_all(self) -> None:
        if self._client is None:
            return
        await self._client.cancel_all_orders()


__all__ = ["CCXTBroker"]
