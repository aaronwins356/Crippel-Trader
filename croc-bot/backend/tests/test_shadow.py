import json
from pathlib import Path

import numpy as np
import pytest

from croc.config import Settings, StorageConfig
from croc.rl import evaluate as evaluate_module
from croc.storage.model_registry import ModelRegistry


class DummyPolicy:
    def predict(self, obs, deterministic=True):
        return np.zeros(1, dtype=float), None


@pytest.fixture(autouse=True)
def patch_loader(monkeypatch):
    monkeypatch.setattr(evaluate_module, "_load_policy", lambda path: DummyPolicy())


def test_shadow_evaluation_logs(tmp_path):
    storage = StorageConfig(
        base_dir=tmp_path,
        ticks=tmp_path / "ticks",
        trades=tmp_path / "trades",
        metrics=tmp_path / "metrics",
    )
    for folder in (storage.base_dir, storage.ticks, storage.trades, storage.metrics):
        folder.mkdir(parents=True, exist_ok=True)

    settings = Settings(storage=storage)
    models_dir = tmp_path / "models"
    registry = ModelRegistry(models_dir)

    baseline_artifact = tmp_path / "baseline.zip"
    baseline_artifact.write_text("baseline")
    baseline_version = registry.register_version(
        baseline_artifact,
        code_sha="baseline",
        metrics={"sharpe": 1.0, "max_drawdown": 0.2, "win_rate": 0.55},
        config={},
    )
    registry.activate(baseline_version.version)

    candidate_artifact = tmp_path / "candidate.zip"
    candidate_artifact.write_text("candidate")
    candidate_version = registry.register_version(
        candidate_artifact,
        code_sha="candidate",
        metrics={"sharpe": 1.2, "max_drawdown": 0.18, "win_rate": 0.6},
        config={},
    )

    result = evaluate_module.evaluate_model(
        settings,
        registry,
        model_path=candidate_version.path,
        shadow=True,
    )

    assert result.log_path is not None
    assert Path(result.log_path).exists()
    lines = Path(result.log_path).read_text().strip().splitlines()
    assert lines, "shadow log should record decisions"
    record = json.loads(lines[0])
    assert "candidate_action" in record and "baseline_action" in record
    assert result.compare_path is not None
    compare = json.loads(Path(result.compare_path).read_text())
    assert "candidate" in compare and "baseline" in compare
