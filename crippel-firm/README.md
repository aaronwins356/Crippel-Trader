# Crippel-Firm – Autonomous Trading Organization

Crippel-Firm is an experimental autonomous trading organization composed of a Manager bot
and a set of specialized worker bots. The Manager hires, evaluates, and, when needed,
terminates worker bots based on their individual performance and the overall health of the
firm. The implementation in this repository focuses on a deterministic simulation suitable
for unit testing and offline experimentation. Real trading integrations are abstracted
behind adapters so they can be replaced with production-ready implementations.

## Features

- **Manager Brain** that tracks firm performance, hires/fires workers, and reallocates
  virtual capital.
- **Event-driven architecture** using an asyncio-based event bus.
- **Worker bot implementations** for research, analysis, trading, and risk management.
- **Paper trading simulator** and Kraken adapter stub for integration testing.
- **FastAPI** service exposing REST and WebSocket endpoints for monitoring and control.
- **Test suite** covering manager decisions, worker lifecycles, and research ingestion.

## Getting Started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m backend.main
```

The default configuration runs the firm in simulation mode and periodically evaluates
bot performance. REST endpoints are available at `http://127.0.0.1:8000` when the API app
is launched.

## Project Structure

See the repository tree for the full module layout. Key modules include:

- `backend/firm/manager.py` – orchestration logic for hiring/firing and evaluation
- `backend/firm/bots/` – implementations of worker bots
- `backend/firm/engine/` – trading simulator and exchange adapter
- `backend/firm/api/` – FastAPI application exposing control endpoints
- `backend/firm/tests/` – unit tests for critical behaviors

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
