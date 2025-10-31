"""Training entrypoint for the reinforcement learning loop."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import typer

try:  # pragma: no cover - imported dynamically in tests
    from stable_baselines3 import DDPG, PPO
except ModuleNotFoundError:  # pragma: no cover
    DDPG = PPO = None  # type: ignore

from ..config import Settings, load_settings
from ..data.features import FeaturePipeline
from ..rl.dataset import ExperienceDataset, build_datasets
from ..storage.model_registry import ModelRegistry
from .env import TradingEnv


@dataclass
class TrainConfig:
    algo: str = "ppo"
    seed: int = 42
    epochs: int = 10
    learning_rate: float = 3e-4
    train_since: Optional[datetime] = None
    train_until: Optional[datetime] = None
    output_dir: Optional[Path] = None


@dataclass
class TrainResult:
    version: str
    model_path: Path
    metrics_path: Path
    config_path: Path
    metadata: dict


def _get_git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001 - fallback in sandboxes
        return "unknown"


def _select_algo(algo: str):
    if PPO is None or DDPG is None:
        raise RuntimeError("stable-baselines3 not available")
    algo = algo.lower()
    if algo == "ppo":
        return PPO
    if algo == "ddpg":
        return DDPG
    raise ValueError(f"Unsupported algorithm: {algo}")


def _run_training(env: TradingEnv, config: TrainConfig):
    algo_cls = _select_algo(config.algo)
    model = algo_cls(
        "MlpPolicy",
        env,
        verbose=0,
        learning_rate=config.learning_rate,
        seed=config.seed,
    )
    total_timesteps = max(config.epochs, 1) * 1_000
    model.learn(total_timesteps=total_timesteps)
    return model


def _evaluate_policy(model, env: TradingEnv, episodes: int = 5) -> dict:
    rewards: list[float] = []
    pnls: list[float] = []
    drawdowns: list[float] = []
    for episode in range(episodes):
        obs, _ = env.reset(seed=model.get_env().np_random.integers(0, 1_000_000) if hasattr(model, "get_env") else None)
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


def train_policy(settings: Settings, registry: ModelRegistry, config: TrainConfig) -> TrainResult:
    """Train a policy and register it in the model registry."""

    symbol = settings.feed.symbol
    pipeline = FeaturePipeline(
        fast_window=int(settings.strategy.params.get("fast_window", 12)),
        slow_window=int(settings.strategy.params.get("slow_window", 26)),
        vol_window=int(settings.strategy.params.get("vol_window", 20)),
    )
    datasets: tuple[ExperienceDataset, ExperienceDataset] | None = None
    try:
        datasets = build_datasets(
            settings.storage,
            symbol=symbol,
            since=config.train_since,
            until=config.train_until,
            pipeline=pipeline,
        )
    except FileNotFoundError:
        datasets = None

    env = TradingEnv(pipeline=pipeline)
    model = _run_training(env, config)
    metrics = _evaluate_policy(model, env)

    base_dir = config.output_dir or Path(settings.storage.base_dir) / "models"
    base_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    run_dir = base_dir / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    model_path = run_dir / "model.zip"
    model.save(str(model_path))

    metadata = {
        "algo": config.algo,
        "seed": config.seed,
        "epochs": config.epochs,
        "learning_rate": config.learning_rate,
        "train_since": config.train_since.isoformat() if config.train_since else None,
        "train_until": config.train_until.isoformat() if config.train_until else None,
        "symbol": symbol,
        "dataset_size": len(datasets[0]) if datasets else 0,
        "eval_dataset_size": len(datasets[1]) if datasets else 0,
    }

    metrics_path = run_dir / "metrics.json"
    config_path = run_dir / "config.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))
    config_path.write_text(json.dumps(metadata, indent=2))

    code_sha = _get_git_sha()
    data_span = None
    if config.train_since and config.train_until:
        data_span = (config.train_since.isoformat(), config.train_until.isoformat())

    registered = registry.register_version(
        model_path,
        code_sha=code_sha,
        metrics=metrics,
        config=metadata,
        data_span=data_span,
    )

    metadata.update({"code_sha": code_sha, "version": registered.version})
    combined_path = run_dir / "metadata.json"
    combined_path.write_text(json.dumps({"metrics": metrics, "config": metadata}, indent=2))

    return TrainResult(
        version=registered.version,
        model_path=registered.path,
        metrics_path=metrics_path,
        config_path=config_path,
        metadata={"metrics": metrics, "config": metadata},
    )


app = typer.Typer(help="Train RL policies for croc")


@app.command()
def train(
    algo: str = typer.Option("ppo", help="Algorithm to train (ppo or ddpg)"),
    seed: int = typer.Option(42, help="RNG seed for reproducibility"),
    epochs: int = typer.Option(10, help="Number of training epochs"),
    lr: float = typer.Option(3e-4, help="Learning rate"),
    train_since: Optional[str] = typer.Option(None, help="ISO timestamp to start training window"),
    train_until: Optional[str] = typer.Option(None, help="ISO timestamp to end training window"),
) -> None:
    settings = load_settings()
    registry = ModelRegistry(Path(settings.storage.base_dir) / "models")
    config = TrainConfig(
        algo=algo,
        seed=seed,
        epochs=epochs,
        learning_rate=lr,
        train_since=datetime.fromisoformat(train_since) if train_since else None,
        train_until=datetime.fromisoformat(train_until) if train_until else None,
    )
    result = train_policy(settings, registry, config)
    registry.activate(result.version)
    typer.echo(json.dumps({"version": result.version, **result.metadata}, indent=2))


if __name__ == "__main__":
    app()
