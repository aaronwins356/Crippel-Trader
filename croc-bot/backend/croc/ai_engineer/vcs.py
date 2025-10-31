"""Repository utilities wrapping git for AI engineer."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .patcher import DiffPatcher


class VCSOperationError(RuntimeError):
    pass


@dataclass
class CommitResult:
    branch: str
    sha: str


class RepositoryManager:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.state_path = repo_root / ".ai_engineer_state.json"

    def commit_diff(self, diff: str, files: Iterable[Path]) -> CommitResult:
        branch = f"ai/{int(time.time())}"
        self._ensure_clean()
        workdir = self.repo_root / f".ai-worktree-{int(time.time())}"
        self._run(["git", "worktree", "add", "-b", branch, str(workdir), "HEAD"])
        try:
            patcher = DiffPatcher(workdir)
            patcher.apply(diff, workdir)
            for file in files:
                self._run(["git", "add", str(file)], cwd=workdir)
            commit_message = "AI engineer suggestion"
            self._run(["git", "commit", "-m", commit_message], cwd=workdir)
            sha = self._run(["git", "rev-parse", "HEAD"], cwd=workdir, capture=True)[1].strip()
        except Exception as exc:
            self._run(["git", "worktree", "remove", "--force", str(workdir)])
            self._run(["git", "branch", "-D", branch], expect_zero=False)
            raise VCSOperationError(str(exc)) from exc
        else:
            self._run(["git", "worktree", "remove", "--force", str(workdir)])
            self._store_state({"branch": branch, "commit": sha})
            return CommitResult(branch=branch, sha=sha)

    def rollback_last(self) -> str:
        state = self._read_state()
        branch = state.get("branch")
        if not branch:
            raise VCSOperationError("No AI engineer branch to rollback")
        self._run(["git", "branch", "-D", branch])
        self._store_state({})
        return branch

    def status(self) -> dict[str, Optional[str]]:
        state = self._read_state()
        return {"branch": state.get("branch"), "commit": state.get("commit")}

    def _ensure_clean(self) -> None:
        code, output = self._run(["git", "status", "--porcelain"], capture=True)
        if output.strip():
            raise VCSOperationError("Working tree dirty; cannot apply AI patch")

    def _run(self, command, cwd: Optional[Path] = None, capture: bool = False, expect_zero: bool = True):
        proc = subprocess.run(
            command,
            cwd=cwd or self.repo_root,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            check=False,
        )
        output = ""
        if capture and proc.stdout:
            output = proc.stdout.decode()
        if expect_zero and proc.returncode != 0:
            stderr = proc.stderr.decode() if proc.stderr else output
            raise VCSOperationError(stderr or f"Command failed: {' '.join(command)}")
        return proc.returncode, output

    def _store_state(self, payload: dict[str, str]) -> None:
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _read_state(self) -> dict[str, str]:
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text(encoding="utf-8"))


__all__ = ["RepositoryManager", "CommitResult", "VCSOperationError"]
