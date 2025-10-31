# croc-bot

croc-bot is a high-performance, internal-use trading research system featuring a FastAPI backend and a Vite/React/Tailwind dashboard. The stack emphasises deterministic configs, strict risk management, and reinforcement learning workflows without any external SaaS dependencies.

## Project Layout

```
croc-bot/
  backend/      # FastAPI app, runtime engine, RL training
  dashboard/    # React + Vite + Tailwind local monitoring UI
  Makefile      # helper targets for dev/test/train/backtest
```

## Prerequisites

- Python 3.11+
- Node.js 18+

## Backend Setup

```bash
cd croc-bot/backend
python -m pip install -U pip
python -m pip install -e .[dev]
cp .env.example .env
python -m croc.app
```

The backend defaults to paper trading with a synthetic replay feed. To enable live trading, set `CROC_MODE=live` and provide `EXCHANGE`, `API_KEY`, and `API_SECRET` in the environment. Live mode is disabled unless all credentials are present.

### Testing

```bash
cd croc-bot/backend
pytest
```

### RL Training & Evaluation

```bash
cd croc-bot/backend
./scripts/train_rl.sh --total-timesteps 50000
./scripts/backtest.sh --episodes 10
```

Models are stored under `backend/storage/models/` and the active model is controlled by an atomic symlink. The runtime hot-reloads whenever the symlink changes.

## Dashboard Setup

```bash
cd croc-bot/dashboard
npm install
npm run dev
```

The dashboard connects to the local FastAPI service (`http://localhost:8000`) and streams ticks, fills, and metrics over WebSockets.

## Make Targets

```bash
make dev        # run the FastAPI app
make test       # run pytest suite
make train      # launch PPO training (Stable-Baselines3)
make backtest   # evaluate active model
```

## License

MIT
