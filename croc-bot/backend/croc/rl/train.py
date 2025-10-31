"""Training entrypoint using Stable-Baselines3."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from stable_baselines3 import PPO

from ..config import load_settings
from ..storage.model_registry import ModelRegistry
from .env import TradingEnv

app = typer.Typer(help="Train RL policies for croc")


@app.command()
def train(
    total_timesteps: int = typer.Option(10_000, help="Total timesteps to train"),
    learning_rate: float = typer.Option(3e-4, help="Optimizer learning rate"),
    seed: int = typer.Option(42, help="RNG seed"),
    model_dir: Optional[Path] = typer.Option(None, help="Directory to store models"),
) -> None:
    settings = load_settings()
    env = TradingEnv()
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=learning_rate,
        verbose=0,
        seed=seed,
    )
    model.learn(total_timesteps=total_timesteps)
    output_dir = model_dir or Path(settings.storage.base_dir) / "models"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    artifact = output_dir / f"ppo_{timestamp}.zip"
    model.save(artifact)
    registry = ModelRegistry(Path(settings.storage.base_dir) / "models")
    registered = registry.register(artifact, {"algo": "PPO", "timesteps": total_timesteps})
    registry.set_active(registered)
    typer.echo(f"Model saved to {registered}")


if __name__ == "__main__":
    app()
