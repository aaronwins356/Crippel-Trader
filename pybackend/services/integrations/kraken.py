"""Lightweight Kraken client stub for live trading simulation."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict

from ...utils.logger import get_child

logger = get_child("kraken")


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


__all__ = ["KrakenClient"]
