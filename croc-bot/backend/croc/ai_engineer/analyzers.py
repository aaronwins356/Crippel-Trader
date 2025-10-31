"""Utilities for detecting hotspots from logs and metrics."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import inspect
from typing import Awaitable, Callable, Deque, Iterable, List

from pydantic import BaseModel, Field


@dataclass
class AnalyzerConfig:
    log_path: Path
    max_logs: int = 500


class IssueKind(str):
    ERROR_CLUSTER = "error_cluster"
    LATENCY_SPIKE = "latency_spike"
    PERFORMANCE_REGIME = "performance_regime"


class IssueEvidence(BaseModel):
    timestamp: datetime
    summary: str
    details: dict[str, object] = Field(default_factory=dict)


class AnalysisSummary(BaseModel):
    summary: str
    issues: list[IssueEvidence] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)


class LogAnalyzer:
    """Parse structured logs for repeated failures."""

    def __init__(self, config: AnalyzerConfig) -> None:
        self.config = config

    def load(self) -> list[dict[str, object]]:
        path = self.config.log_path
        if not path.exists():
            return []
        lines = deque(maxlen=self.config.max_logs)
        with path.open() as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                lines.append(data)
        return list(lines)

    def cluster_errors(self, logs: Iterable[dict[str, object]]) -> list[IssueEvidence]:
        clusters: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
        for row in logs:
            key = str(row.get("stack_hash")) if row.get("stack_hash") else row.get("message", "unknown")
            if row.get("level") in {"ERROR", "CRITICAL"}:
                clusters[key].append(row)
        evidences: list[IssueEvidence] = []
        for key, items in clusters.items():
            if len(items) < 3:
                continue
            latest = max(items, key=lambda item: item.get("timestamp", ""))
            summary = latest.get("message", "error")
            evidences.append(
                IssueEvidence(
                    timestamp=_parse_ts(latest.get("timestamp")),
                    summary=f"{summary} (x{len(items)})",
                    details={"event": IssueKind.ERROR_CLUSTER, "stack_hash": key},
                )
            )
        return evidences


Fetcher = Callable[[], dict[str, float] | Awaitable[dict[str, float]]]


class MetricsAnalyzer:
    """Aggregate runtime metrics for spikes and regressions."""

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher
        self.history: Deque[dict[str, float]] = deque(maxlen=64)

    async def snapshot(self) -> dict[str, float]:
        metrics = self.fetcher()
        if inspect.isawaitable(metrics):  # pragma: no cover - async path
            metrics = await metrics
        metrics["timestamp"] = datetime.utcnow().isoformat()
        self.history.append(metrics)
        return metrics

    def detect_spikes(self) -> list[IssueEvidence]:
        if len(self.history) < 5:
            return []
        tail: List[dict[str, float]] = list(self.history)[-5:]
        latencies = [row.get("loop_p99_ms", 0.0) for row in tail]
        inference = [row.get("inference_p99_ms", 0.0) for row in tail]
        pnl = [row.get("pnl_1h", 0.0) for row in tail]
        evidences: list[IssueEvidence] = []
        if _is_spike(latencies):
            evidences.append(
                IssueEvidence(
                    timestamp=datetime.utcnow(),
                    summary="Loop latency p99 spiking",
                    details={"event": IssueKind.LATENCY_SPIKE, "values": latencies},
                )
            )
        if _is_spike(inference):
            evidences.append(
                IssueEvidence(
                    timestamp=datetime.utcnow(),
                    summary="Inference latency p99 spiking",
                    details={"event": IssueKind.LATENCY_SPIKE, "values": inference},
                )
            )
        if pnl and pnl[-1] < min(pnl[:-1]):
            evidences.append(
                IssueEvidence(
                    timestamp=datetime.utcnow(),
                    summary="PNL 1h deteriorating",
                    details={"event": IssueKind.PERFORMANCE_REGIME, "values": pnl},
                )
            )
        return evidences


async def build_analysis(log_analyzer: LogAnalyzer, metrics_analyzer: MetricsAnalyzer) -> AnalysisSummary:
    logs = log_analyzer.load()
    error_evidence = log_analyzer.cluster_errors(logs)
    metrics = await metrics_analyzer.snapshot()
    metrics_evidence = metrics_analyzer.detect_spikes()
    issues = sorted(error_evidence + metrics_evidence, key=lambda item: item.timestamp, reverse=True)
    summary = _summarise(issues)
    return AnalysisSummary(summary=summary, issues=issues, metrics={k: float(v) for k, v in metrics.items() if k != "timestamp"})


def _summarise(issues: Iterable[IssueEvidence]) -> str:
    if not issues:
        return "System nominal"
    counts = Counter(issue.details.get("event", "other") for issue in issues)
    parts = [f"{kind}: {count}" for kind, count in counts.items()]
    return ", ".join(parts)


def _parse_ts(value: object) -> datetime:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return datetime.utcnow()


def _is_spike(values: List[float]) -> bool:
    if len(values) < 5:
        return False
    baseline = statistics.fmean(values[:-1])
    if baseline == 0:
        return False
    return values[-1] > baseline * 1.5


__all__ = [
    "AnalyzerConfig",
    "AnalysisSummary",
    "LogAnalyzer",
    "MetricsAnalyzer",
    "build_analysis",
]
