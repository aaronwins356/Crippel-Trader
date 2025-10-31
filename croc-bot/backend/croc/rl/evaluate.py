"""Evaluation harness for trained models."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Optional

import typer
from stable_baselines3 import PPO

from ..config import load_settings
from ..storage.model_registry import ModelRegistry
from .env import TradingEnv

app = typer.Typer(help="Evaluate trained models")


@app.command()
def evaluate(
    model_path: Optional[Path] = typer.Option(None, help="Path to model artifact"),
    episodes: int = typer.Option(5, help="Number of evaluation episodes"),
    seed: int = typer.Option(7, help="Random seed base"),
) -> None:
    settings = load_settings()
    registry = ModelRegistry(Path(settings.storage.base_dir) / "models")
    artifact = model_path or registry.active_model()
    if artifact is None:
        raise typer.BadParameter("No active model found")
    env = TradingEnv()
    model = PPO.load(str(artifact), env=env)
    rewards: list[float] = []
    pnls: list[float] = []
    for episode in range(episodes):
        obs, _ = env.reset(seed=seed + episode)
        done = False
        total_reward = 0.0
        last_info = {}
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            done = terminated or truncated
            last_info = info
        rewards.append(total_reward)
        pnls.append(float(last_info.get("pnl", 0.0)))
    summary = {
        "model": str(artifact),
        "episodes": episodes,
        "avg_reward": mean(rewards),
        "avg_pnl": mean(pnls),
        "max_reward": max(rewards),
        "min_reward": min(rewards),
    }
    output_path = Path(settings.storage.metrics) / "evaluation.json"
    output_path.write_text(json.dumps(summary, indent=2))
    typer.echo(json.dumps(summary, indent=2))


if __name__ == "__main__":
    app()
