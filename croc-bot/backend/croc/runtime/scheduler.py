"""Async scheduler coordinating recurring maintenance jobs."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Optional

from ..bus import EventBus


@dataclass
class Job:
    name: str
    interval: timedelta
    handler: Callable[[], Awaitable[Any]]
    next_run: datetime = field(default_factory=lambda: datetime.utcnow())
    task: Optional[asyncio.Task[Any]] = None


class Scheduler:
    def __init__(self, bus: Optional[EventBus] = None) -> None:
        self._jobs: list[Job] = []
        self._running = False
        self._bus = bus
        self._loop_task: Optional[asyncio.Task[Any]] = None

    def add_job(self, interval: timedelta, handler: Callable[[], Awaitable[Any]], *, name: str) -> None:
        job = Job(name=name, interval=interval, handler=handler)
        job.next_run = datetime.utcnow() + interval
        self._jobs.append(job)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._loop_task = asyncio.create_task(self._run_loop(), name="scheduler-loop")

    async def stop(self) -> None:
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._loop_task
            self._loop_task = None

    async def _run_loop(self) -> None:
        try:
            while self._running:
                now = datetime.utcnow()
                due_jobs = [job for job in self._jobs if job.next_run <= now]
                for job in due_jobs:
                    job.next_run = now + job.interval
                    asyncio.create_task(self._execute(job))
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:  # pragma: no cover
            return

    async def _execute(self, job: Job) -> None:
        try:
            await job.handler()
            if self._bus:
                await self._bus.publish("scheduler.job", {"job": job.name, "status": "success"})
        except Exception as exc:  # noqa: BLE001
            if self._bus:
                await self._bus.publish(
                    "scheduler.job",
                    {"job": job.name, "status": "error", "detail": str(exc)},
                )


__all__ = ["Scheduler"]
