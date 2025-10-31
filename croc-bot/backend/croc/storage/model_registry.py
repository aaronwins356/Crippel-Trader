"""Local model registry with atomic activation."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from filelock import FileLock


class ModelRegistry:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.active_link = self.base_dir / "active"
        self.lock = FileLock(str(self.base_dir / "registry.lock"))

    def register(self, artifact: Path, metadata: dict) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        dest = self.base_dir / timestamp
        dest.mkdir(parents=True, exist_ok=False)
        target = dest / artifact.name
        shutil.copy2(artifact, target)
        with (dest / "metadata.json").open("w") as fh:
            json.dump(metadata, fh, indent=2)
        return target

    def set_active(self, artifact: Path) -> None:
        with self.lock:
            tmp_link = self.base_dir / "active.tmp"
            if tmp_link.exists() or tmp_link.is_symlink():
                tmp_link.unlink()
            tmp_link.symlink_to(artifact.resolve())
            tmp_link.replace(self.active_link)

    def active_model(self) -> Optional[Path]:
        if not self.active_link.exists():
            return None
        return self.active_link.resolve()

    def list_models(self) -> list[Path]:
        return sorted(
            (
                path
                for path in self.base_dir.iterdir()
                if path.is_dir() and path.name != "active"
            ),
            reverse=True,
        )

    def load_metadata(self, artifact: Path) -> dict:
        meta_path = artifact.parent / "metadata.json"
        if not meta_path.exists():
            return {}
        return json.loads(meta_path.read_text())


__all__ = ["ModelRegistry"]
