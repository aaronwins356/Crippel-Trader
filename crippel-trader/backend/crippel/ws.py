"""WebSocket streaming helpers."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket

from .models.core import BackpressureConfig


class ConnectionManager:
    """Manage WebSocket connections with bounded queues."""

    def __init__(self, backpressure: BackpressureConfig | None = None) -> None:
        self._backpressure = backpressure or BackpressureConfig()
        self._connections: dict[WebSocket, asyncio.Queue[dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._backpressure.max_queue)
        async with self._lock:
            self._connections[websocket] = queue

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.pop(websocket, None)
        await websocket.close()

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast message to all connected WebSocket clients.
        
        Ensures message has required structure with safe defaults.
        """
        # Define default schema for safety
        default_payload = {
            "critical_alerts": [],
            "warnings": [],
            "info": [],
        }
        
        # Merge with actual message, preserving existing values
        if "payload" in message and isinstance(message["payload"], dict):
            # Only add defaults for missing keys
            for key, default_value in default_payload.items():
                if key not in message["payload"]:
                    message["payload"][key] = default_value
        
        async with self._lock:
            websockets = list(self._connections.items())
        for websocket, queue in websockets:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                if self._backpressure.drop_policy == "oldest":
                    _ = queue.get_nowait()
                    queue.put_nowait(message)
                else:
                    continue
            asyncio.create_task(self._flush(websocket, queue))

    async def _flush(self, websocket: WebSocket, queue: asyncio.Queue[dict[str, Any]]) -> None:
        while not queue.empty():
            message = await queue.get()
            try:
                await websocket.send_json(message)
            except Exception:
                await self.disconnect(websocket)
                break
