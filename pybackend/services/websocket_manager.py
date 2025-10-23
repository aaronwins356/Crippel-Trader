"""WebSocket connection manager for FastAPI routes."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Set

from fastapi import WebSocket

from ..utils.logger import get_child

logger = get_child("ws")


class WebSocketManager:
    def __init__(self) -> None:
        self.connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._loop = asyncio.get_running_loop()
        async with self._lock:
            self.connections.add(websocket)
        logger.info("WebSocket client connected")

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self.connections.discard(websocket)
        logger.info("WebSocket client disconnected")

    async def broadcast(self, payload: Any) -> None:
        message = json.dumps(payload, default=self._json_serializer)
        async with self._lock:
            connections = list(self.connections)
        for websocket in connections:
            try:
                await websocket.send_text(message)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Failed to send WebSocket message", exc_info=exc)
                await self.disconnect(websocket)

    def dispatch(self, payload: Any) -> None:
        if not self.connections or not self._loop:
            return
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None
        if running_loop and running_loop is self._loop:
            asyncio.create_task(self.broadcast(payload))
        else:
            asyncio.run_coroutine_threadsafe(self.broadcast(payload), self._loop)

    @staticmethod
    def _json_serializer(value: Any) -> Any:
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return value


__all__ = ["WebSocketManager"]
