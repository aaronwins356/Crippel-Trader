"""Manager brain running evaluation loop."""
from __future__ import annotations

import asyncio
from typing import Optional

from ..logging import get_logger
from ..settings import AppSettings
from .manager import ManagerBot


class ManagerBrain:
    """High level coordinator for the firm."""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.manager = ManagerBot(settings)
        self.logger = get_logger("brain")
        self._task: Optional[asyncio.Task[None]] = None
        self._running = asyncio.Event()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        await self.manager.ensure_staffing()
        self._running.set()
        self._task = asyncio.create_task(self._run_loop())

    async def _run_loop(self) -> None:
        interval = self.settings.hiring.eval_interval_sec
        while self._running.is_set():
            scores = await self.manager.run_once()
            self.logger.info("evaluation", scores=scores)
            await asyncio.sleep(interval)

    async def stop(self) -> None:
        self._running.clear()
        if self._task:
            await self.manager.shutdown()
            await self._task
            self._task = None
