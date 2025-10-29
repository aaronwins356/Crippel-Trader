"""Automated refactoring assistant that collaborates with a local Qwen model."""
from __future__ import annotations

import argparse
import asyncio
import ast
import difflib
import hashlib
import json
import logging
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from ..config import get_settings
from .client import LMStudioClient

_LOGGER_NAME = "ai_refactor"
_STATE_VERSION = 1
_DEFAULT_TARGETS = (
    "start_croc_bot.py",
    "start_real_trading.py",
    "crippel-trader/backend/main.py",
    "crippel-trader/backend/crippel/enhanced_trading_system.py",
    "crippel-trader/backend/crippel/real_trading_engine.py",
    "crippel-trader/backend/crippel/risk_manager.py",
    "crippel-trader/backend/crippel/engine",
    "crippel-trader/backend/crippel/models",
    "crippel-trader/backend/crippel/strategies",
    "crippel-trader/backend/crippel/services",
)
_SKIP_DIR_NAMES = {".git", "__pycache__", "node_modules", "venv", ".venv", "migrations"}


def _slice_source(source: str, start: int, end: int) -> str:
    lines = source.splitlines()
    slice_lines = lines[start - 1 : end]
    return "\n".join(slice_lines)


@dataclass(slots=True)
class CodeEntity:
    """Describes a refactorable code fragment within a file."""

    path: Path
    relative_path: Path
    entity_type: str
    name: str
    start_line: int
    end_line: int
    source: str
    def prompt(self) -> str:
        """Generate a specialized prompt for the entity."""
        scope_hint = self._determine_scope_hint()
        return (
            f"{scope_hint}\n\n"
            f"Refactor and optimize the following {self.entity_type} while preserving all risk controls, "
            f"fees, and integration points. Return updated code and a concise explanation.\n\n"
            f"```python\n{self.source}\n```"
        )

    def _determine_scope_hint(self) -> str:
        lowered = "/".join(self.relative_path.parts).lower()
        if "strategy" in lowered:
            return "Suggest improvements to how this strategy handles slippage, fees, and execution edge cases."
        if "risk" in lowered:
            return "Audit this risk management logic for capital limits, drawdown safety, and determinism."
        if self.relative_path.name in {"models.py"} or "models" in lowered:
            return "Optimize this model for performance, validation, and clarity."
        if self.relative_path.name in {"main.py", "run.py"}:
            return "Review this entry point for reliability, configuration safety, and startup resilience."
        return "Optimize this component for performance, safety, and clarity within Croc-Bot's trading system."

    def refresh(self) -> bool:
        """Reload the entity from disk to ensure accurate boundaries before refactoring."""
        text = self.path.read_text()
        if self.entity_type == "module":
            self.start_line = 1
            self.end_line = len(text.splitlines())
            self.source = text
            return True
        try:
            tree = ast.parse(text, filename=str(self.relative_path), type_comments=True)
        except SyntaxError:
            self.start_line = 1
            self.end_line = len(text.splitlines())
            self.source = text
            return True
        for node in tree.body:
            if self._matches_node(node):
                self.start_line = getattr(node, "lineno", 1)
                self.end_line = getattr(node, "end_lineno", self.start_line)
                self.source = _slice_source(text, self.start_line, self.end_line)
                return True
        return False

    def _matches_node(self, node: ast.AST) -> bool:
        if isinstance(node, ast.ClassDef) and self.entity_type == "class":
            return node.name == self.name
        if isinstance(node, ast.AsyncFunctionDef) and self.entity_type == "async function":
            return node.name == self.name
        if isinstance(node, ast.FunctionDef) and self.entity_type == "function":
            return node.name == self.name
        return False


class StateManager:
    """Persists hashes of processed files to avoid redundant work."""

    def __init__(self, state_path: Path) -> None:
        self._path = state_path
        self._data: dict[str, object] = {"version": _STATE_VERSION, "files": {}}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text())
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(raw, dict):
            return
        if raw.get("version") != _STATE_VERSION:
            return
        files = raw.get("files")
        if isinstance(files, dict):
            self._data = {"version": _STATE_VERSION, "files": files}

    def should_skip(self, relative_path: Path, file_hash: str, *, force: bool) -> bool:
        if force:
            return False
        files = self._data.get("files", {})
        if not isinstance(files, dict):
            return False
        record = files.get(str(relative_path))
        if isinstance(record, dict):
            recorded_hash = record.get("sha")
            if isinstance(recorded_hash, str) and recorded_hash == file_hash:
                return True
        return False

    def update(self, relative_path: Path, file_hash: str) -> None:
        files = self._data.setdefault("files", {})
        if not isinstance(files, dict):
            files = {}
            self._data["files"] = files
        files[str(relative_path)] = {
            "sha": file_hash,
            "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2, sort_keys=True))


class CodeScanner:
    """Collects Python entities that should be offered for refactoring."""

    def __init__(self, project_root: Path, targets: Sequence[str] | None = None) -> None:
        self._project_root = project_root
        self._targets = tuple(targets or _DEFAULT_TARGETS)

    def scan(self) -> Iterable[tuple[Path, Path, list[CodeEntity]]]:
        for file_path, relative_path in self._iter_python_files():
            source = file_path.read_text()
            try:
                tree = ast.parse(source, filename=str(relative_path), type_comments=True)
            except SyntaxError:
                yield (
                    file_path,
                    relative_path,
                    [
                        CodeEntity(
                            path=file_path,
                            relative_path=relative_path,
                            entity_type="module",
                            name=relative_path.stem,
                            start_line=1,
                            end_line=len(source.splitlines()),
                            source=source,
                        )
                    ],
                )
                continue
            nodes = [
                node
                for node in tree.body
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            if not nodes:
                yield (
                    file_path,
                    relative_path,
                    [
                        CodeEntity(
                            path=file_path,
                            relative_path=relative_path,
                            entity_type="module",
                            name=relative_path.stem,
                            start_line=1,
                            end_line=len(source.splitlines()),
                            source=source,
                        )
                    ],
                )
                continue
            entities: list[CodeEntity] = []
            for node in nodes:
                start = getattr(node, "lineno", 1)
                end = getattr(node, "end_lineno", start)
                snippet = _slice_source(source, start, end)
                entity_type = (
                    "class"
                    if isinstance(node, ast.ClassDef)
                    else "async function"
                    if isinstance(node, ast.AsyncFunctionDef)
                    else "function"
                )
                entities.append(
                    CodeEntity(
                        path=file_path,
                        relative_path=relative_path,
                        entity_type=entity_type,
                        name=getattr(node, "name", relative_path.stem),
                        start_line=start,
                        end_line=end,
                        source=snippet,
                    )
                )
            yield file_path, relative_path, entities

    def _iter_python_files(self) -> Iterable[tuple[Path, Path]]:
        for target in self._targets:
            resolved = (self._project_root / target).resolve()
            if resolved.is_dir():
                yield from self._walk_directory(resolved)
            elif resolved.is_file() and resolved.suffix == ".py":
                yield resolved, resolved.relative_to(self._project_root)

    def _walk_directory(self, directory: Path) -> Iterable[tuple[Path, Path]]:
        for path in directory.rglob("*.py"):
            if any(part in _SKIP_DIR_NAMES for part in path.parts):
                continue
            try:
                relative = path.relative_to(self._project_root)
            except ValueError:
                continue
            yield path, relative


class RefactorAssistant:
    """Coordinates scanning, prompting, and applying code refactors."""

    def __init__(self, *, batch: bool, force: bool, test_cmd: Sequence[str] | None = None, targets: Sequence[str] | None = None) -> None:
        settings = get_settings()
        self._project_root = settings.project_root
        self._logs_dir = self._project_root / "logs"
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        self._logger = logging.getLogger(_LOGGER_NAME)
        self._configure_logging()
        self._logger.debug("initializing refactor assistant", root=str(self._project_root))
        self._scanner = CodeScanner(self._project_root, targets)
        self._state = StateManager(self._project_root / ".cache" / "ai_refactor_state.json")
        self._client = LMStudioClient(
            base_url=str(settings.lmstudio_api_base),
            model=settings.lmstudio_model,
            timeout=settings.ai_request_timeout,
        )
        self._batch = batch
        self._force = force
        self._test_cmd = list(test_cmd) if test_cmd else None
        self._applied_changes: list[Path] = []

    def _configure_logging(self) -> None:
        if self._logger.handlers:
            return
        self._logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(self._logs_dir / "ai_refactor.log")
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(file_handler)
        self._logger.addHandler(stream_handler)

    async def run(self) -> None:
        try:
            await self._process_entities()
        finally:
            await self._client.aclose()
            self._state.save()
            if self._applied_changes and self._test_cmd:
                self._run_tests()

    async def _process_entities(self) -> None:
        for file_path, relative_path, entities in self._scanner.scan():
            file_hash = hashlib.sha1(file_path.read_bytes()).hexdigest()
            if self._state.should_skip(relative_path, file_hash, force=self._force):
                self._logger.debug("Skipping %s (unchanged)", relative_path)
                continue
            for entity in entities:
                await self._handle_entity(entity)
            new_hash = hashlib.sha1(file_path.read_bytes()).hexdigest()
            self._state.update(relative_path, new_hash)

    async def _handle_entity(self, entity: CodeEntity) -> None:
        self._logger.info("\n📄 Processing %s (%s)", entity.relative_path, entity.name)
        if not entity.refresh():
            self._logger.warning("Unable to locate current source for %s", entity.name)
            return
        prompt = entity.prompt()
        response = await self._request_refactor(prompt)
        if response is None:
            self._logger.warning("Skipping %s due to empty response", entity.name)
            return
        new_code, explanation = self._extract_code_and_explanation(response)
        if not new_code:
            self._logger.warning("No code block detected for %s", entity.name)
            return
        self._logger.info("Explanation:\n%s", explanation.strip() or "(no explanation provided)")
        diff_text = self._render_diff(entity.source, new_code, entity)
        if diff_text:
            self._logger.info("Diff:\n%s", diff_text)
        if not self._batch:
            choice = input("Apply this change? (y/n) ").strip().lower()
            if choice not in {"y", "yes"}:
                self._logger.info("Skipped change for %s", entity.name)
                return
        self._apply_change(entity, new_code)
        self._applied_changes.append(entity.relative_path)
        self._logger.info("Applied change to %s", entity.relative_path)

    async def _request_refactor(self, prompt: str) -> str | None:
        messages = [
            {"role": "system", "content": "You are a senior Python trading system engineer."},
            {
                "role": "user",
                "content": "Refactor the following component and explain your improvements:\n\n" + prompt,
            },
        ]
        try:
            return await self._client.chat(messages, temperature=0.2)
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.error("Model request failed: %s", exc)
            return None

    @staticmethod
    def _extract_code_and_explanation(response: str) -> tuple[str, str]:
        code_match = re.search(r"```(?:python)?\n(.*?)```", response, flags=re.DOTALL)
        if not code_match:
            return "", response
        code = code_match.group(1).strip()
        explanation = (response[: code_match.start()] + response[code_match.end() :]).strip()
        return code, explanation

    def _render_diff(self, original: str, new_code: str, entity: CodeEntity) -> str:
        original_lines = original.strip("\n").splitlines()
        new_lines = new_code.strip("\n").splitlines()
        diff = difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"before/{entity.relative_path}:{entity.name}",
            tofile=f"after/{entity.relative_path}:{entity.name}",
            lineterm="",
        )
        return "\n".join(diff)

    def _apply_change(self, entity: CodeEntity, new_code: str) -> None:
        source = entity.path.read_text()
        lines = source.splitlines()
        prefix = lines[: entity.start_line - 1]
        suffix = lines[entity.end_line :]
        new_lines = new_code.strip("\n").splitlines()
        updated = prefix + new_lines + suffix
        entity.path.write_text("\n".join(updated) + "\n")

    def _run_tests(self) -> None:
        assert self._test_cmd is not None
        self._logger.info("\n🧪 Running test command: %s", " ".join(self._test_cmd))
        try:
            result = subprocess.run(self._test_cmd, check=False, capture_output=True, text=True)
        except OSError as exc:  # pragma: no cover - defensive logging
            self._logger.error("Failed to execute test command: %s", exc)
            return
        if result.stdout:
            self._logger.info(result.stdout.strip())
        if result.stderr:
            self._logger.error(result.stderr.strip())
        if result.returncode == 0:
            self._logger.info("✅ Tests completed successfully")
        else:
            self._logger.warning("⚠️ Tests exited with code %s", result.returncode)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI-powered refactoring assistant for Croc-Bot")
    parser.add_argument("--batch", action="store_true", help="Automatically apply all suggested changes")
    parser.add_argument("--force", action="store_true", help="Ignore cached file hashes and rescan everything")
    parser.add_argument(
        "--test-cmd",
        nargs=argparse.REMAINDER,
        help="Command to run after applying changes (e.g. --test-cmd pytest)",
    )
    parser.add_argument(
        "--targets",
        nargs="*",
        help="Optional list of files or directories to analyze instead of the defaults",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    assistant = RefactorAssistant(
        batch=args.batch,
        force=args.force,
        test_cmd=args.test_cmd,
        targets=args.targets,
    )
    asyncio.run(assistant.run())


if __name__ == "__main__":
    main()
