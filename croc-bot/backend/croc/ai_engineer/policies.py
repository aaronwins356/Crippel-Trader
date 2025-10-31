"""Guardrails for AI-generated patches."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Set


class PolicyViolation(RuntimeError):
    pass


@dataclass
class ChangePolicies:
    allowlist: Set[str] = field(default_factory=set)
    denylist: Set[str] = field(default_factory=set)
    sensitive: Set[str] = field(default_factory=set)

    def validate(self, files: Iterable[Path], allow_add_dep: bool) -> None:
        for file in files:
            path_str = str(file)
            if any(path_str.startswith(entry) for entry in self.denylist):
                raise PolicyViolation(f"Changes to {path_str} are not permitted")
            if self.allowlist and not any(path_str.startswith(entry) for entry in self.allowlist):
                raise PolicyViolation(f"File {path_str} is outside AI allowlist")
            if not allow_add_dep and path_str.endswith("pyproject.toml"):
                raise PolicyViolation("Dependency updates require allow_add_dep flag")

    @classmethod
    def default(cls) -> "ChangePolicies":
        return cls(
            allowlist={
                "backend/croc/strategy",
                "backend/croc/data",
                "backend/croc/features.py",
                "backend/croc/runtime",
                "backend/croc/logging_cfg.py",
                "backend/croc/ai_engineer",
                "backend/croc/app.py",
                "backend/croc/models",
                "backend/croc/storage",
                "dashboard/src",
            },
            denylist={
                "backend/croc/risk/risk_manager.py",
                "backend/croc/exec/broker_ccxt.py",
                "backend/croc/config",
                "backend/croc/app_security",
            },
            sensitive={"backend/croc/risk"},
        )


__all__ = ["ChangePolicies", "PolicyViolation"]
