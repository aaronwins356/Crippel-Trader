"""Async job scheduler for snapshots and maintenance tasks."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Job:
    interval: float
    handler: Callable[[], Awaitable[Any]]
    task: asyncio.Task[Any] | None = None


class Scheduler:
    def __init__(self) -> None:
        self._jobs: list[Job] = []
        self._running = False

    def add_job(self, interval: float, handler: Callable[[], Awaitable[Any]]) -> None:
        self._jobs.append(Job(interval=interval, handler=handler))

    async def _run_job(self, job: Job) -> None:
        while self._running:
            await job.handler()
            await asyncio.sleep(job.interval)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        for job in self._jobs:
            job.task = asyncio.create_task(self._run_job(job))

    async def stop(self) -> None:
        self._running = False
        for job in self._jobs:
            if job.task:
                job.task.cancel()
        await asyncio.gather(
            *(job.task for job in self._jobs if job.task),
            return_exceptions=True,
        )
        for job in self._jobs:
            job.task = None


__all__ = ["Scheduler"]
