# CrocBot 🐊

**CrocBot** is a production-ready research sandbox for systematic traders. Built on Python 3.11+, it delivers a clean, modular
architecture for experimenting with quantitative ideas while keeping simulations deterministic, logs transparent, and risk controls
a front-and-center priority. This project is provided **for educational purposes only** and should not be treated as financial
advice.

## 🚀 Why CrocBot
- Config-driven workflow that boots in minutes
- Deterministic synthetic market feed for reliable experiments
- Moving-average crossover reference strategy with guardrails
- Built-in risk controls for drawdowns, stop-losses, and sizing
- Paper trading ledger that tracks balance, equity, and PnL
- Extension hooks for ML/RL models, execution adapters, and AI copilots

## 🧠 System Architecture at a Glance
- `data/` – ingestion utilities and feature engineering helpers
- `models/` – reusable model interfaces and RL adapters
- `strategies/` – strategy factories that stay model-aware
- `executors/` – async order routing and venue abstractions
- `pipelines/` – training, evaluation, and deployment flows
- `orchestration/` – event loops that coordinate data, inference, and orders
- `utils/` – shared logging, configuration, metrics, and dependency injection

For deeper guidance, visit `docs/ARCHITECTURE.md`.

## 🧩 Prerequisites
- Python 3.11+
- Recommended: `virtualenv` or `venv`

## ✅ Quick Launch Guide
1. **Create an isolated environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   ```
2. **Install CrocBot and developer tooling**
   ```bash
   pip install -e .[dev]
   ```
3. **Review or tweak the simulation config** in `config/config.json` (see the breakdown below).
4. **Run the paper-trading engine**
   ```bash
   python -m croc_bot.orchestration.cli --config config/config.json
   ```
5. **Inspect logs and results** in the console output to validate strategy behaviour.

## 🛠 Configuration Cheatsheet
`config/config.json` centralizes all runtime knobs:

```json
{
  "trading": { "max_steps": 500 },
  "feed": {
    "symbol": "FAKE-USD",
    "interval_seconds": 1,
    "initial_price": 100.0,
    "volatility": 0.5,
    "seed": 42
  },
  "strategy": { "fast_window": 5, "slow_window": 12 },
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

Key fields:
- `trading.max_steps` – maximum number of ticks to simulate
- `feed.*` – parameters for the deterministic synthetic price stream
- `strategy.fast_window` & `strategy.slow_window` – moving-average window sizes
- `risk.*` – drawdown, stop-loss, sizing, and notional caps
- `simulation.*` – paper trading balance and fee assumptions

## 🧪 Run Tests
```bash
pytest
```

## ⚠️ Disclaimer
CrocBot simplifies market structure and omits real-world concerns such as latency, slippage, liquidity, and exchange
connectivity. Do not deploy it for live trading without extensive enhancements, validations, and risk reviews.
