"""Async event loop coordinating data, models, and execution."""
from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from typing import Awaitable, Callable

import pandas as pd

from data.ingestion import MarketDataStream
from strategies.base import ModelDrivenStrategy
from utils.logging import get_logger
from utils.metrics import LATENCY, ORDERS_ACCEPTED, ORDERS_REJECTED, ORDERS_SUBMITTED


async def run_live_loop(
    *,
    data_stream: MarketDataStream,
    strategy: ModelDrivenStrategy,
    submit_order: Callable[[pd.DataFrame], Awaitable[None]],
    shutdown_event: asyncio.Event | None = None,
) -> None:
    """Drive the main trading loop with graceful shutdown semantics."""

    logger = get_logger(__name__, strategy=strategy.name)
    shutdown_event = shutdown_event or asyncio.Event()

    async with AsyncExitStack() as stack:
        stack.callback(logger.info, "live_loop_stopped")
        logger.info("live_loop_started")

        async for frame in data_stream:
            if shutdown_event.is_set():
                break

            ORDERS_SUBMITTED.inc()

            async with LATENCY.time():
                try:
                    await strategy.on_bar(frame)
                    await submit_order(frame)
                except Exception as exc:  # pragma: no cover - defensive logging
                    ORDERS_REJECTED.inc()
                    logger.exception("live_loop_error", error=str(exc))
                else:
                    ORDERS_ACCEPTED.inc()

            await asyncio.sleep(0)

        shutdown_event.set()
        await stack.aclose()
