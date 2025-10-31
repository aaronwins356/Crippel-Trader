"""Versioned model registry with atomic activation and rollback."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from filelock import FileLock


@dataclass(frozen=True)
class ModelVersion:
    version: str
    created_at: datetime
    path: Path
    code_sha: str
    data_span: tuple[str, str] | None
    metrics: dict[str, Any]
    config: dict[str, Any]

    @classmethod
    def from_dict(cls, base_dir: Path, payload: dict[str, Any]) -> "ModelVersion":
        return cls(
            version=payload["version"],
            created_at=datetime.fromisoformat(payload["created_at"]),
            path=base_dir / payload["version"] / payload["model_file"],
            code_sha=payload.get("code_sha", "unknown"),
            data_span=tuple(payload.get("data_span")) if payload.get("data_span") else None,
            metrics=payload.get("metrics", {}),
            config=payload.get("config", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "model_file": self.path.name,
            "code_sha": self.code_sha,
            "data_span": list(self.data_span) if self.data_span else None,
            "metrics": self.metrics,
            "config": self.config,
        }


class ModelRegistry:
    """Track model versions and expose atomic activation helpers."""

    def __init__(self, base_dir: Path, keep_last: int = 10) -> None:
        self.base_dir = base_dir
        self.keep_last = keep_last
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.active_link = self.base_dir / "active"
        self.index_path = self.base_dir / "index.json"
        self.lock = FileLock(str(self.base_dir / "registry.lock"))

    def register_version(
        self,
        artifact: Path,
        *,
        code_sha: str,
        metrics: dict[str, Any],
        config: dict[str, Any],
        data_span: tuple[str, str] | None = None,
    ) -> ModelVersion:
        with self.lock:
            version = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
            version_dir = self.base_dir / version
            version_dir.mkdir(parents=True, exist_ok=False)
            target = version_dir / artifact.name
            shutil.copy2(artifact, target)
            created_at = datetime.now(UTC)
            metadata = ModelVersion(
                version=version,
                created_at=created_at,
                path=target,
                code_sha=code_sha,
                data_span=data_span,
                metrics=metrics,
                config=config,
            )
            self._write_metadata(version_dir, metadata)
            index = self._load_index()
            index.insert(0, metadata.to_dict())
            if len(index) > self.keep_last:
                for stale in index[self.keep_last :]:
                    self._prune_version(stale["version"])
                index = index[: self.keep_last]
            self._write_index(index)
            return metadata

    def activate(self, version: str) -> ModelVersion:
        with self.lock:
            metadata = self._get_version(version)
            self._activate_path(metadata.path)
            return metadata

    def rollback(self, version: Optional[str] = None) -> ModelVersion:
        with self.lock:
            index = self._load_index()
            if not index:
                raise FileNotFoundError("no versions available for rollback")
            if version is None:
                active = self.active_version()
                if active is None:
                    version = index[0]["version"]
                else:
                    candidates = [item for item in index if item["version"] != active.version]
                    if not candidates:
                        raise FileNotFoundError("no previous model to rollback to")
                    version = candidates[0]["version"]
            metadata = self._get_version(version)
            self._activate_path(metadata.path)
            return metadata

    def active_model(self) -> Optional[Path]:
        if not self.active_link.exists():
            return None
        return self.active_link.resolve()

    def active_version(self) -> Optional[ModelVersion]:
        if not self.active_link.exists():
            return None
        target = self.active_link.resolve()
        version = target.parent.name
        return self._get_version(version)

    def list_versions(self) -> list[ModelVersion]:
        index = self._load_index()
        return [ModelVersion.from_dict(self.base_dir, item) for item in index]

    def load_metadata(self, version: str) -> dict[str, Any]:
        version_dir = self.base_dir / version
        meta_path = version_dir / "metadata.json"
        if not meta_path.exists():
            return {}
        return json.loads(meta_path.read_text())

    def _load_index(self) -> list[dict[str, Any]]:
        if not self.index_path.exists():
            return []
        return json.loads(self.index_path.read_text())

    def _write_index(self, index: list[dict[str, Any]]) -> None:
        self.index_path.write_text(json.dumps(index, indent=2))

    def _prune_version(self, version: str) -> None:
        version_dir = self.base_dir / version
        if version_dir.exists():
            shutil.rmtree(version_dir)

    def _activate_path(self, artifact: Path) -> None:
        tmp_link = self.base_dir / "active.tmp"
        if tmp_link.exists() or tmp_link.is_symlink():
            tmp_link.unlink()
        tmp_link.symlink_to(artifact.resolve())
        tmp_link.replace(self.active_link)

    def _write_metadata(self, version_dir: Path, metadata: ModelVersion) -> None:
        meta_path = version_dir / "metadata.json"
        meta_path.write_text(json.dumps(metadata.to_dict(), indent=2))

    def _get_version(self, version: str) -> ModelVersion:
        index = self._load_index()
        for item in index:
            if item["version"] == version:
                return ModelVersion.from_dict(self.base_dir, item)
        raise FileNotFoundError(f"version {version} not found")


__all__ = ["ModelRegistry", "ModelVersion"]
