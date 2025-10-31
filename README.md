# CrocBot

CrocBot is a minimal, extensible trading bot framework written in Python 3.11+. It focuses on clean architecture, deterministic simulations, and clear logging so you can experiment with trading ideas safely. The current implementation simulates a moving-average crossover strategy on a synthetic market data feed. **This project is for educational purposes only and is not financial advice.**

## Features
- Config-driven architecture with JSON configuration
- Deterministic synthetic market data feed (random walk)
- Simple moving-average crossover strategy
- Risk management for drawdown, stop-loss, and position sizing
- Paper trading simulation with balance, equity, and PnL tracking
- Optional AI assistant integration point

## Modular Architecture

The repository now ships with a modular scaffold optimized for ML/RL-driven
trading workloads. New top-level packages include:

- `data/` – market data ingestion and feature engineering utilities
- `models/` – standardized model interfaces and RL integration helpers
- `strategies/` – model-aware strategy abstractions and factories
- `executors/` – async order execution and venue adapters
- `pipelines/` – online/offline training flows
- `orchestration/` – event loops coordinating live data, inference, and orders
- `utils/` – shared logging, configuration, metrics, and dependency injection

See `docs/ARCHITECTURE.md` for migration guidance and wiring examples.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\\Scripts\\activate
pip install -e .[dev]
```

## Configuration

All runtime parameters are defined in `config/config.json`.

```json
{
  "trading": {
    "max_steps": 500
  },
  "feed": {
    "symbol": "FAKE-USD",
    "interval_seconds": 1,
    "initial_price": 100.0,
    "volatility": 0.5,
    "seed": 42
  },
  "strategy": {
    "fast_window": 5,
    "slow_window": 12
  },
  "risk": {
    "max_drawdown": 0.2,
    "stop_loss_pct": 0.05,
    "position_size_pct": 0.1,
    "max_position_value": 1000.0
  },
  "simulation": {
    "starting_balance": 10000.0,
    "trading_fee_bps": 5
  }
}
```

- `trading.max_steps`: Maximum number of ticks to simulate.
- `feed.*`: Parameters controlling the deterministic synthetic price stream.
- `strategy.fast_window` & `slow_window`: Window sizes for the moving averages.
- `risk.*`: Constraints on drawdown, stop-loss trigger, and position sizing.
- `simulation.*`: Paper trading settings such as starting cash and trading fees.

## Usage

After installation, run the bot in paper mode:

```bash
python -m core.bot --config config/config.json --mode paper
```

## Testing

```bash
pytest
```

## Disclaimer

This repository demonstrates a simplified simulation and omits real-world complexities such as latency, slippage, liquidity, and exchange connectivity. Do not use it for live trading without significant enhancements and thorough testing.
