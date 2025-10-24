import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

module = importlib.import_module("backend.firm")
sys.modules.setdefault("firm", module)
for submodule in [
    "config",
    "manager",
    "economy",
    "eventbus",
    "registry",
    "brain",
    "interfaces",
    "utils.logging",
    "utils.metrics",
    "bots.base",
    "bots.trader_bot",
    "bots.research_bot",
    "bots.analyst_bot",
    "bots.risk_bot",
    "engine.kraken_adapter",
    "engine.simulator",
    "engine.portfolio",
    "engine.evaluation",
    "data.insider_parser",
    "data.sentiment_scraper",
    "data.indicators",
]:
    sys.modules.setdefault(f"firm.{submodule}", importlib.import_module(f"backend.firm.{submodule}"))
