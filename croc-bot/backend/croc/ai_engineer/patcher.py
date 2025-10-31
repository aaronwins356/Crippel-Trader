"""Utilities for applying unified diffs safely."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Set


class PatchApplicationError(RuntimeError):
    pass


@dataclass
class PatchResult:
    files: Set[Path]


class DiffPatcher:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def extract_changed_files(self, diff: str) -> Set[Path]:
        files: Set[Path] = set()
        for line in diff.splitlines():
            if line.startswith("+++ b/") and line[6:] != "/dev/null":
                files.add(Path(line[6:]))
            elif line.startswith("--- a/") and line[6:] != "/dev/null":
                files.add(Path(line[6:]))
        return files

    def apply(self, diff: str, workdir: Path | None = None) -> PatchResult:
        target = workdir or self.repo_root
        self._run(["git", "apply", "--check", "-"], diff, cwd=target)
        self._run(["git", "apply", "-"], diff, cwd=target)
        files = self.extract_changed_files(diff)
        self._run_python_syntax(files, target)
        return PatchResult(files=files)

    def _run_python_syntax(self, files: Iterable[Path], workdir: Path) -> None:
        python_files = [f for f in files if f.suffix == ".py"]
        if not python_files:
            return
        rel_paths = []
        base = workdir.resolve()
        for path in python_files:
            candidate = (workdir / path).resolve()
            if not candidate.exists():
                continue
            rel_paths.append(str(candidate.relative_to(base)))
        if not rel_paths:
            return
        command = ["python", "-m", "py_compile", *rel_paths]
        self._run(command, cwd=workdir)

    def _run(self, command: List[str], diff: str | None = None, cwd: Path | None = None) -> None:
        proc = subprocess.run(
            command,
            input=diff.encode("utf-8") if diff else None,
            cwd=cwd or self.repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode != 0:
            raise PatchApplicationError(proc.stderr.decode())


__all__ = ["DiffPatcher", "PatchApplicationError", "PatchResult"]
