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

## AI Self-Reconfiguration & Local Simulation Mode

- Set `MODE=AI_SIMULATION` (or `CROC_MODE=AI_SIMULATION`) in `.env` to run without exchange credentials.
- If you request live trading against Kraken without providing API keys, the backend automatically falls back to simulation and prints `⚙️ Running in AI Simulation Mode` during startup.
- The bot uses a stochastic price generator and logs parameter adaptations to both the console and `logs/ai_simulation.log`.
- Use `GET /mode` to inspect the current mode and `POST /mode` with `{ "mode": "AI_SIMULATION" }` or `{ "mode": "LIVE_TRADING" }` to switch at runtime.
- Re-enable Kraken live trading by setting `CROC_MODE=live` (or posting `LIVE_TRADING`) and providing `EXCHANGE=kraken`, `API_KEY`, `API_SECRET`, and (optionally) `API_PASSPHRASE`.

## Dashboard Setup

```bash
cd croc-bot/dashboard
npm install
npm run dev
```

The dashboard connects to the local FastAPI service (`http://localhost:8000`) and streams ticks, fills, and metrics over WebSockets.

## AI Engineer

The automated AI engineer monitors logs, runtime metrics, and Git history to propose and validate performance or robustness fixes.

### REST API

```bash
# Request a suggestion for a suspected slow SMA loop
curl -X POST http://localhost:8000/ai/suggest \
  -H "Content-Type: application/json" \
  -d '{"issue": "Investigate SMA loop latency spikes", "contextFiles": ["backend/croc/strategy/rule_sma.py"]}'

# Apply a previously returned diff after sandbox validation
curl -X POST http://localhost:8000/ai/apply \
  -H "Content-Type: application/json" \
  -d '{"diff": "<unified diff from suggest>", "allow_add_dep": false}'

# Roll back the last AI-generated branch
curl -X POST http://localhost:8000/ai/rollback

# Inspect the latest analysis, diff, and sandbox results
curl http://localhost:8000/ai/status
```

### Dashboard Workflow

- Open the dashboard (`npm run dev`) and locate the **AI Engineer** panel.
- Enter an issue description and optional context files to request a diff.
- Review the unified diff preview with keyboard navigation, run sandbox checks, and apply if all gates pass.
- Streamed AI events and sandbox results are visible in real time for audit and approval.

## Make Targets

```bash
make dev        # run the FastAPI app
make test       # run pytest suite
make train      # launch PPO training (Stable-Baselines3)
make backtest   # evaluate active model
```

## License

MIT
