"""Entry point orchestrating CrocBot components."""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from .feed import FeedConfig, PriceFeed
from .risk import RiskConfig, RiskManager
from .simulation import SimulationConfig, SimulationEngine
from .strategy import MovingAverageCrossoverStrategy, StrategyConfig


LOGGER = logging.getLogger("croc_bot")


def configure_logging() -> None:
    """Configure logging for the application."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )


def load_config(path: Path) -> dict[str, Any]:
    """Load configuration from a JSON file."""

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def run_bot(config_path: Path, mode: str) -> None:
    """Run the trading bot in the requested mode."""

    if mode != "paper":
        raise ValueError("Only paper trading mode is currently supported.")

    raw_config = load_config(config_path)

    feed_config = FeedConfig(**raw_config["feed"])
    strategy_config = StrategyConfig(**raw_config["strategy"])
    risk_config = RiskConfig(**raw_config["risk"])
    simulation_config = SimulationConfig(**raw_config["simulation"])
    max_steps = int(raw_config["trading"]["max_steps"])

    feed = PriceFeed(feed_config)
    strategy = MovingAverageCrossoverStrategy(strategy_config)
    risk_manager = RiskManager(risk_config)
    simulation = SimulationEngine(simulation_config)
    stream = feed.stream()

    LOGGER.info("Starting CrocBot in %s mode", mode)

    for step in range(max_steps):
        market_tick = next(stream)
        simulation.update_market(market_tick.price)
        signal = strategy.update(market_tick.price)
        account_before = simulation.account_state()
        decision = risk_manager.assess(signal, market_tick.price, account_before)

        if decision.signal != signal:
            LOGGER.debug(
                "Risk override: strategy=%s, risk=%s", signal.name, decision.signal.name
            )

        simulation.execute_trade(decision.signal, market_tick.price, decision.notional_value)
        account_after = simulation.account_state()

        LOGGER.info(
            "Step=%s price=%.2f signal=%s cash=%.2f equity=%.2f position=%.4f",
            step + 1,
            market_tick.price,
            decision.signal.name,
            account_after.cash,
            account_after.equity,
            account_after.position_units,
        )

    final_state = simulation.account_state()
    LOGGER.info(
        "Finished. Cash=%.2f Equity=%.2f Drawdown=%.2f%% Trades=%s",
        final_state.cash,
        final_state.equity,
        final_state.drawdown * 100,
        len(simulation.trade_log),
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Run the CrocBot trading simulation.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/config.json"),
        help="Path to the JSON configuration file.",
    )
    parser.add_argument(
        "--mode",
        choices=["paper"],
        default="paper",
        help="Trading mode to use.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point for the trading bot."""

    configure_logging()
    args = parse_args()
    run_bot(args.config, args.mode)


if __name__ == "__main__":
    main()
