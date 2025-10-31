"""Command-line entry point for Croc-Bot."""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from .config import BotConfig, load_config
from .engine import TradingEngineBuilder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Croc-Bot trading engine")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/config.json"),
        help="Path to configuration file",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Override the configured maximum number of steps",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    max_steps = args.max_steps or config.trading.max_steps
    engine = TradingEngineBuilder(config).build()
    asyncio.run(engine.run(max_steps=max_steps))


if __name__ == "__main__":  # pragma: no cover
    main()
