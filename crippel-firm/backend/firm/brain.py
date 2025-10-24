"""Manager brain orchestrating evaluation loops."""
from __future__ import annotations

import asyncio
from typing import Optional

from .config import FirmConfig
from .manager import ManagerBot
from .utils.logging import get_logger


class ManagerBrain:
    """High-level controller running the manager loop."""

    def __init__(self, config: FirmConfig) -> None:
        self.config = config
        self.manager = ManagerBot(config)
        self.logger = get_logger("brain")
        self._task: Optional[asyncio.Task[None]] = None
        self._running = asyncio.Event()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._running.set()
        await self.manager.ensure_staffing()
        self._task = asyncio.create_task(self._run())
        await self._task

    async def _run(self) -> None:
        interval = self.config.hiring.eval_interval_seconds
        while self._running.is_set():
            scores = await self.manager.run_once()
            self.logger.info("Manager evaluation scores: %s", scores)
            await asyncio.sleep(interval)

    async def stop(self) -> None:
        self._running.clear()
        if self._task:
            await self.manager.shutdown()
            await self._task
