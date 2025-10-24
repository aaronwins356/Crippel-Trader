"""WebSocket fanout for firm events."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from .firm.manager import ManagerBot
from .routes import get_manager

ws_router = APIRouter()


@ws_router.websocket("/ws/stream")
async def stream(websocket: WebSocket, manager: ManagerBot = Depends(get_manager)) -> None:
    await websocket.accept()
    topics = ["signals", "orders:intent", "orders:fill", "risk:halt", "research:idea"]
    queues = []
    tasks: dict[asyncio.Task[Any], tuple[str, asyncio.Queue[Any]]] = {}
    try:
        for topic in topics:
            queue = await manager.event_bus.subscribe(topic)
            queues.append((topic, queue))
            task = asyncio.create_task(queue.get())
            tasks[task] = (topic, queue)
        while True:
            done, _ = await asyncio.wait(tasks.keys(), return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                topic, queue = tasks.pop(task)
                payload = task.result()
                await websocket.send_json({"topic": topic, "payload": payload})
                new_task = asyncio.create_task(queue.get())
                tasks[new_task] = (topic, queue)
    except WebSocketDisconnect:
        return
    finally:
        for topic, queue in queues:
            await manager.event_bus.unsubscribe(topic, queue)
