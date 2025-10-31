"""Learning loop scheduler orchestrating dataset aggregation and promotion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from ..bus import EventBus
from ..config import Settings
from ..risk.risk_manager import RiskManager
from ..storage.model_registry import ModelRegistry, ModelVersion
from .gates import GateResult, PromotionGates
from .promote import Promoter
from .train import TrainConfig, TrainResult, train_policy
from .evaluate import EvaluationResult, evaluate_model


@dataclass
class ScheduledJobState:
    last_run: Optional[datetime] = None
    last_result: Optional[dict] = None
    error: Optional[str] = None


@dataclass
class LearningSchedule:
    settings: Settings
    registry: ModelRegistry
    promoter: Promoter
    bus: EventBus
    risk: RiskManager
    gates: PromotionGates = field(default_factory=PromotionGates)
    nightly_at: timedelta = field(default=timedelta(hours=24))
    weekly_at: timedelta = field(default=timedelta(days=7))

    train_state: ScheduledJobState = field(default_factory=ScheduledJobState)
    eval_state: ScheduledJobState = field(default_factory=ScheduledJobState)
    promote_state: ScheduledJobState = field(default_factory=ScheduledJobState)
    shadow_status: dict | None = None

    async def run_training(self, config: Optional[TrainConfig] = None) -> TrainResult:
        config = config or TrainConfig()
        result = train_policy(self.settings, self.registry, config)
        self.train_state.last_run = datetime.utcnow()
        self.train_state.last_result = {
            "version": result.version,
            "metadata": result.metadata,
        }
        await self.bus.publish("rl.train.completed", self.train_state.last_result)
        return result

    async def run_evaluation(self, version: Optional[str] = None, shadow: bool = False) -> EvaluationResult:
        artifact: Optional[ModelVersion] = None
        if version:
            artifact = next((model for model in self.registry.list_versions() if model.version == version), None)
            if artifact is None:
                raise FileNotFoundError(f"version {version} not found for evaluation")
        result = evaluate_model(self.settings, self.registry, model_path=artifact.path if artifact else None, shadow=shadow)
        self.eval_state.last_run = datetime.utcnow()
        payload = {"metrics": result.metrics, "shadow": shadow}
        if artifact:
            payload["version"] = artifact.version
        if result.compare_path:
            payload["compare_path"] = str(result.compare_path)
        if result.log_path:
            payload["shadow_log"] = str(result.log_path)
            self.shadow_status = {
                "log": str(result.log_path),
                "compare": str(result.compare_path) if result.compare_path else None,
                "started_at": self.eval_state.last_run.isoformat(),
            }
        self.eval_state.last_result = payload
        await self.bus.publish("rl.evaluate.completed", payload)
        return result

    async def run_promotion(self, version: str, candidate_metrics: dict) -> GateResult:
        baseline = self.registry.active_version()
        if baseline is None:
            raise FileNotFoundError("no active baseline to compare against")
        latency_payload = {
            "candidate": {"latency_p99": candidate_metrics.get("latency_p99", 0.0)},
            "baseline": {"latency_p99": baseline.metrics.get("latency_p99", 0.0)},
        }
        gate_result = self.gates.evaluate(candidate_metrics, baseline.metrics, latency_payload)
        self.promote_state.last_run = datetime.utcnow()
        payload = {
            "version": version,
            "passed": gate_result.passed,
            "reasons": gate_result.reasons,
        }
        self.promote_state.last_result = payload
        if gate_result.passed:
            promoted = await self.promoter.promote(version)
            self.risk.set_model_tier("new")
            payload["active"] = promoted.version
        await self.bus.publish("rl.promote.result", payload)
        return gate_result

    async def rollback(self, version: Optional[str] = None) -> ModelVersion:
        rolled = await self.promoter.rollback(version)
        self.risk.set_model_tier("active")
        await self.bus.publish("rl.rollback", {"version": rolled.version})
        return rolled

    def get_shadow_status(self) -> dict | None:
        return self.shadow_status


__all__ = ["LearningSchedule"]
