"""Ephemeral sandbox for validating AI-generated patches."""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from .patcher import DiffPatcher, PatchApplicationError


@dataclass
class SandboxReport:
    success: bool
    steps: list[dict[str, str]] = field(default_factory=list)

    def model_dump(self) -> dict[str, object]:
        return {"success": self.success, "steps": self.steps}


class SandboxRunner:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    async def run(self, diff: str) -> SandboxReport:
        with tempfile.TemporaryDirectory(prefix="ai-eng-") as tmpdir:
            workdir = Path(tmpdir)
            self._run(["git", "worktree", "add", "--detach", str(workdir), "HEAD"], cwd=self.repo_root)
            try:
                patch = DiffPatcher(workdir)
                try:
                    patch.apply(diff, workdir)
                except PatchApplicationError as exc:
                    return SandboxReport(False, steps=[{"name": "apply", "status": "failed", "output": str(exc)}])
                checks = [
                    ("ruff", ["ruff", "--select=E,F", "."]),
                    ("mypy", ["mypy", "croc"]),
                    ("pytest", ["pytest", "-q"]),
                    ("backtest", ["python", "-m", "croc.rl.evaluate", "--quick"]),
                ]
                steps: list[dict[str, str]] = []
                for name, command in checks:
                    result = self._run(command, cwd=workdir, capture=True, expect_zero=False)
                    steps.append({"name": name, "status": "passed" if result[0] == 0 else "failed", "output": result[1]})
                    if result[0] != 0:
                        return SandboxReport(False, steps=steps)
                return SandboxReport(True, steps=steps)
            finally:
                self._run(["git", "worktree", "remove", "--force", str(workdir)], cwd=self.repo_root)

    def _run(self, command: List[str], cwd: Path, capture: bool = False, expect_zero: bool = True) -> tuple[int, str]:
        proc = subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.STDOUT if capture else None,
            check=False,
        )
        output = proc.stdout.decode() if capture and proc.stdout else ""
        if expect_zero and proc.returncode != 0:
            raise RuntimeError(output or f"Command failed: {' '.join(command)}")
        return proc.returncode, output


__all__ = ["SandboxRunner", "SandboxReport"]
