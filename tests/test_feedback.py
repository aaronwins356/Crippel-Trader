"""Tests for the closed-loop feedback pipeline."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from data.experience import FileExperienceRepository, TradeExperience

from pipelines.feedback import (
    AcceptanceCriteria,
    EvaluationBackend,
    EvaluationReport,
    FeedbackLoop,
    ModelVersion,
    RiskPolicy,
    TrainingBackend,
)


class DummyTrainer(TrainingBackend):
    def __init__(self) -> None:
        self.trained = False

    def train(self, experiences: pd.DataFrame, baseline: ModelVersion | None) -> ModelVersion:
        self.trained = True
        return ModelVersion(version="v1", path="/tmp/model", trained_at=datetime.now(timezone.utc))


class DummyEvaluator(EvaluationBackend):
    def __init__(self, report: EvaluationReport) -> None:
        self._report = report
        self.evaluated = False

    def evaluate(self, candidate: ModelVersion, baseline: ModelVersion | None) -> EvaluationReport:
        self.evaluated = True
        return self._report


class DummyDeployer:
    def __init__(self) -> None:
        self.deployed = False
        self.shadowed = False

    def deploy(self, candidate: ModelVersion, report: EvaluationReport) -> None:
        self.deployed = True

    def shadow(self, candidate: ModelVersion) -> None:
        self.shadowed = True


def _experience_repo(tmp_path: Path) -> FileExperienceRepository:
    repo = FileExperienceRepository(tmp_path / "exp.jsonl")
    experience = TradeExperience(
        timestamp=datetime.now(timezone.utc),
        symbol="TEST",
        state={"feature": 1.0},
        action="BUY",
        reward=10.0,
        done=False,
        info={},
    )
    repo.append([experience])
    return repo


def test_feedback_loop_deploys_on_success(tmp_path) -> None:
    repo = _experience_repo(tmp_path)
    trainer = DummyTrainer()
    report = EvaluationReport(metrics={"sharpe": 1.5, "max_drawdown": 0.05, "win_rate": 0.6}, stress_failures=())
    evaluator = DummyEvaluator(report)
    deployer = DummyDeployer()
    criteria = AcceptanceCriteria(min_sharpe=1.0, max_drawdown=0.1, min_win_rate=0.55)
    loop = FeedbackLoop(repo, trainer, evaluator, deployer, RiskPolicy(criteria))

    artifacts = loop.run_once()

    assert artifacts.decision is not None and artifacts.decision.promote
    assert deployer.deployed and not deployer.shadowed


def test_feedback_loop_shadows_when_below_threshold(tmp_path) -> None:
    repo = _experience_repo(tmp_path)
    trainer = DummyTrainer()
    report = EvaluationReport(metrics={"sharpe": 0.5, "max_drawdown": 0.05, "win_rate": 0.6}, stress_failures=())
    evaluator = DummyEvaluator(report)
    deployer = DummyDeployer()
    criteria = AcceptanceCriteria(min_sharpe=1.0, max_drawdown=0.1, min_win_rate=0.55)
    loop = FeedbackLoop(repo, trainer, evaluator, deployer, RiskPolicy(criteria))

    artifacts = loop.run_once()

    assert artifacts.decision is not None and not artifacts.decision.promote
    assert artifacts.decision.shadow
    assert deployer.shadowed and not deployer.deployed

