"""Promotion gate checks for candidate policies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable


@dataclass(slots=True)
class GateResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PromotionGates:
    latency_key: str = "latency_p99"
    sharpe_key: str = "sharpe"
    drawdown_key: str = "max_drawdown"
    winrate_key: str = "win_rate"
    non_regression_tests: Iterable[Callable[[], bool]] = ()

    def evaluate(self, candidate: dict, baseline: dict, latency: dict | None = None) -> GateResult:
        reasons: list[str] = []
        latency = latency or {}
        if candidate.get(self.sharpe_key, 0.0) < baseline.get(self.sharpe_key, float("-inf")):
            reasons.append("Sharpe ratio regressed")
        if candidate.get(self.drawdown_key, float("inf")) > baseline.get(self.drawdown_key, float("inf")):
            reasons.append("Max drawdown exceeded baseline")
        if candidate.get(self.winrate_key, 0.0) < baseline.get(self.winrate_key, float("-inf")):
            reasons.append("Win rate regressed")
        if latency:
            if latency.get("candidate", {}).get(self.latency_key, float("inf")) > latency.get("baseline", {}).get(
                self.latency_key, float("inf")
            ):
                reasons.append("Latency regression")
        for check in self.non_regression_tests:
            try:
                if not check():
                    reasons.append("Non-regression check failed")
            except Exception as exc:  # noqa: BLE001
                reasons.append(f"Non-regression check error: {exc}")
        return GateResult(passed=not reasons, reasons=reasons)


__all__ = ["PromotionGates", "GateResult"]
