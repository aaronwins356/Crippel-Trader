# Croc Bot Backend

Croc Bot is a modular trading engine built on FastAPI, asyncio, and reinforcement learning. The backend exposes REST and WebSocket interfaces for monitoring, control, and streaming telemetry.

## Features

- Deterministic configuration via `.env` + YAML/JSON
- Paper and live execution modes (live requires CCXT credentials)
- Strategy runtime supporting rule-based and ML policies
- Async core pipeline with strict risk management and observability
- RL training and evaluation harness powered by Stable-Baselines3

## Getting Started

```bash
python -m pip install -e .[dev]
cp .env.example .env
python -m croc.app
```

Use `pytest` to run the test suite.
