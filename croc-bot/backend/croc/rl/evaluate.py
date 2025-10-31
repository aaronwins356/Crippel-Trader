"""Evaluation and shadow testing for trained models."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

import numpy as np
import typer

try:  # pragma: no cover - optional for tests
    from stable_baselines3 import PPO
except ModuleNotFoundError:  # pragma: no cover
    PPO = None  # type: ignore

from ..config import Settings, load_settings
from ..storage.model_registry import ModelRegistry, ModelVersion
from .env import TradingEnv


@dataclass
class EvaluationResult:
    metrics: dict
    compare_path: Optional[Path]
    log_path: Optional[Path]


def _load_policy(path: Path):
    if PPO is None:
        raise RuntimeError("stable-baselines3 not available")
    return PPO.load(str(path))


def _evaluate_policy(model, env: TradingEnv, episodes: int = 5) -> dict:
    rewards: list[float] = []
    pnls: list[float] = []
    drawdowns: list[float] = []
    for episode in range(episodes):
        obs, _ = env.reset(seed=episode)
        done = False
        total_reward = 0.0
        pnl = 0.0
        max_dd = 0.0
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            pnl = float(info.get("pnl", pnl))
            max_dd = max(max_dd, float(info.get("drawdown", 0.0)))
            done = terminated or truncated
        rewards.append(total_reward)
        pnls.append(pnl)
        drawdowns.append(max_dd)
    return {
        "avg_reward": float(np.mean(rewards)),
        "avg_pnl": float(np.mean(pnls)),
        "max_drawdown": float(np.max(drawdowns)),
    }


def _shadow_compare(
    candidate,
    baseline,
    env: TradingEnv,
    log_dir: Path,
    episodes: int = 2,
) -> tuple[dict, Path, Path]:
    shadow_log = log_dir / "shadow.jsonl"
    compare_path = log_dir / "compare.json"
    with shadow_log.open("w") as fh:
        for episode in range(episodes):
            obs, _ = env.reset(seed=episode + 10)
            done = False
            while not done:
                cand_action, _ = candidate.predict(obs, deterministic=True)
                base_action, _ = baseline.predict(obs, deterministic=True)
                next_obs, reward, terminated, truncated, info = env.step(base_action)
                fh.write(
                    json.dumps(
                        {
                            "timestamp": datetime.now(UTC).isoformat(),
                            "episode": episode,
                            "candidate_action": cand_action.tolist(),
                            "baseline_action": base_action.tolist(),
                            "reward": reward,
                            "info": info,
                        }
                    )
                    + "\n"
                )
                obs = next_obs
                done = terminated or truncated
    candidate_metrics = _evaluate_policy(candidate, env)
    baseline_metrics = _evaluate_policy(baseline, env)
    comparison = {
        "candidate": candidate_metrics,
        "baseline": baseline_metrics,
        "delta": {
            key: float(candidate_metrics.get(key, 0.0) - baseline_metrics.get(key, 0.0))
            for key in candidate_metrics
        },
    }
    compare_path.write_text(json.dumps(comparison, indent=2))
    return comparison, compare_path, shadow_log


def evaluate_model(
    settings: Settings,
    registry: ModelRegistry,
    *,
    model_path: Optional[Path] = None,
    shadow: bool = False,
) -> EvaluationResult:
    env = TradingEnv()
    artifact = model_path or registry.active_model()
    if artifact is None:
        raise FileNotFoundError("no model available for evaluation")
    candidate = _load_policy(artifact)
    metrics = _evaluate_policy(candidate, env)
    compare_path: Optional[Path] = None
    log_path: Optional[Path] = None
    if shadow:
        baseline_version: Optional[ModelVersion] = registry.active_version()
        if baseline_version is None:
            raise FileNotFoundError("no active baseline to shadow")
        baseline = _load_policy(baseline_version.path)
        shadow_dir = Path(settings.storage.base_dir) / "shadow" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        shadow_dir.mkdir(parents=True, exist_ok=True)
        comparison, compare_path, log_path = _shadow_compare(candidate, baseline, env, shadow_dir)
        metrics = comparison["candidate"]
    return EvaluationResult(metrics=metrics, compare_path=compare_path, log_path=log_path)


app = typer.Typer(help="Evaluate trained models")


@app.command()
def evaluate(
    model_path: Optional[Path] = typer.Option(None, help="Path to model artifact"),
    shadow: bool = typer.Option(False, help="Enable shadow evaluation against active model"),
) -> None:
    settings = load_settings()
    registry = ModelRegistry(Path(settings.storage.base_dir) / "models")
    result = evaluate_model(settings, registry, model_path=model_path, shadow=shadow)
    output = {"metrics": result.metrics}
    if result.compare_path:
        output["compare_path"] = str(result.compare_path)
    if result.log_path:
        output["shadow_log"] = str(result.log_path)
    typer.echo(json.dumps(output, indent=2))


if __name__ == "__main__":
    app()
