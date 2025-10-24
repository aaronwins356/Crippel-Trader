"""WebSocket broadcast of firm metrics."""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..manager import ManagerBot


router = APIRouter()


async def metrics_stream(manager: ManagerBot) -> AsyncIterator[dict[str, float]]:
    while True:
        await asyncio.sleep(2)
        yield manager.economy.performance_summary()


@router.websocket("/ws/metrics")
async def metrics(ws: WebSocket, manager: ManagerBot) -> None:
    await ws.accept()
    try:
        async for snapshot in metrics_stream(manager):
            await ws.send_json(snapshot)
    except WebSocketDisconnect:
        return
