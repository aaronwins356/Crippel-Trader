"""Run backend and frontend smoke checks."""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


async def run_backend() -> None:
    proc = await asyncio.create_subprocess_exec(
        "uvicorn",
        "main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        cwd=str(ROOT / "backend"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    await asyncio.sleep(2)
    proc.terminate()
    await proc.wait()


async def run_frontend() -> None:
    proc = await asyncio.create_subprocess_exec(
        "npm",
        "run",
        "build",
        cwd=str(ROOT / "frontend"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    await proc.wait()


async def main() -> None:
    await asyncio.gather(run_backend(), run_frontend())


if __name__ == "__main__":
    asyncio.run(main())
