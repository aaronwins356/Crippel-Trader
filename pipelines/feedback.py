"""Closed-loop feedback pipeline for continuous model improvement."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Protocol

import pandas as pd

from data.experience import ExperienceRepository
from data.performance import PerformanceSummary


@dataclass(slots=True)
class ModelVersion:
    """Metadata describing a trained model artifact."""

    version: str
    path: str
    trained_at: datetime


@dataclass(slots=True)
class EvaluationReport:
    """Evaluation output produced by the test harness."""

    metrics: dict[str, float]
    stress_failures: tuple[str, ...]
    baseline_metrics: dict[str, float] | None = None

    def metric(self, name: str, default: float = 0.0) -> float:
        return float(self.metrics.get(name, default))


class TrainingBackend(Protocol):
    """Component responsible for fitting a model from experiences."""

    def train(self, experiences: pd.DataFrame, baseline: ModelVersion | None) -> ModelVersion:
        ...


class EvaluationBackend(Protocol):
    """Executes backtests and stress tests for a candidate model."""

    def evaluate(self, candidate: ModelVersion, baseline: ModelVersion | None) -> EvaluationReport:
        ...


class DeploymentBackend(Protocol):
    """Deploys an approved model into the live environment."""

    def deploy(self, candidate: ModelVersion, report: EvaluationReport) -> None:
        ...

    def shadow(self, candidate: ModelVersion) -> None:
        ...


@dataclass(slots=True)
class PromotionDecision:
    """Represents the outcome of risk and performance checks."""

    promote: bool
    shadow: bool
    reasons: tuple[str, ...] = ()


class Decision(Enum):
    """High-level decision states for model promotion."""

    REJECT = auto()
    SHADOW = auto()
    PROMOTE = auto()


@dataclass(slots=True)
class AcceptanceCriteria:
    """Thresholds that a candidate must satisfy."""

    min_sharpe: float
    max_drawdown: float
    min_win_rate: float
    require_stress_free: bool = True


class RiskPolicy:
    """Applies acceptance criteria to evaluation reports."""

    def __init__(self, criteria: AcceptanceCriteria) -> None:
        self._criteria = criteria

    def assess(self, report: EvaluationReport) -> PromotionDecision:
        sharpe = report.metric("sharpe")
        drawdown = report.metric("max_drawdown")
        win_rate = report.metric("win_rate")
        reasons: list[str] = []
        promote = True

        if sharpe < self._criteria.min_sharpe:
            promote = False
            reasons.append(f"Sharpe below threshold: {sharpe:.2f} < {self._criteria.min_sharpe:.2f}")
        if drawdown > self._criteria.max_drawdown:
            promote = False
            reasons.append(
                f"Drawdown above threshold: {drawdown:.2%} > {self._criteria.max_drawdown:.2%}"
            )
        if win_rate < self._criteria.min_win_rate:
            promote = False
            reasons.append(f"Win rate below threshold: {win_rate:.2%} < {self._criteria.min_win_rate:.2%}")
        if self._criteria.require_stress_free and report.stress_failures:
            promote = False
            reasons.append("Stress tests failed: " + ", ".join(report.stress_failures))

        shadow = not promote and not report.stress_failures
        return PromotionDecision(promote=promote, shadow=shadow, reasons=tuple(reasons))


@dataclass(slots=True)
class FeedbackArtifacts:
    """Artifacts produced after a feedback cycle completes."""

    model: ModelVersion | None
    evaluation: EvaluationReport | None
    decision: PromotionDecision | None
    performance: PerformanceSummary | None


class FeedbackLoop:
    """Coordinates end-to-end training, testing, and deployment."""

    def __init__(
        self,
        experience_repo: ExperienceRepository,
        trainer: TrainingBackend,
        evaluator: EvaluationBackend,
        deployer: DeploymentBackend,
        policy: RiskPolicy,
        *,
        experience_window: int | None = None,
    ) -> None:
        self._experience_repo = experience_repo
        self._trainer = trainer
        self._evaluator = evaluator
        self._deployer = deployer
        self._policy = policy
        self._experience_window = experience_window
        self._latest_model: ModelVersion | None = None
        self._latest_performance: PerformanceSummary | None = None

    def run_once(self) -> FeedbackArtifacts:
        experiences = self._experience_repo.load(limit=self._experience_window)
        if experiences.empty:
            return FeedbackArtifacts(model=None, evaluation=None, decision=None, performance=None)

        candidate = self._trainer.train(experiences, self._latest_model)
        evaluation = self._evaluator.evaluate(candidate, self._latest_model)
        decision = self._policy.assess(evaluation)

        if decision.promote:
            self._deployer.deploy(candidate, evaluation)
            self._latest_model = candidate
        elif decision.shadow:
            self._deployer.shadow(candidate)
        else:
            self._latest_model = self._latest_model

        return FeedbackArtifacts(
            model=candidate,
            evaluation=evaluation,
            decision=decision,
            performance=self._latest_performance,
        )

    def update_live_performance(self, summary: PerformanceSummary) -> None:
        """Provide the latest live results for context during evaluation."""

        self._latest_performance = summary


__all__ = [
    "ModelVersion",
    "EvaluationReport",
    "TrainingBackend",
    "EvaluationBackend",
    "DeploymentBackend",
    "AcceptanceCriteria",
    "RiskPolicy",
    "FeedbackLoop",
    "FeedbackArtifacts",
]

