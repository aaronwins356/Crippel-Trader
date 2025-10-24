# Crippel Trader

Crippel Trader is a deterministic crypto trading stack that supports paper and live execution, market prediction, and a live dashboard. It is designed for a single operator (Aaron) with a focus on safety, reproducibility, and fast tick-to-signal performance.

## Safety First

> **LIVE trading routes orders directly to Kraken. Double-check credentials and confirm mode switches manually.**
>
> The repository deliberately ships without any compiled assets or binaries. All files are human-readable text, and any required logos or build artefacts are represented as inline placeholders.

## Features

- FastAPI backend with asynchronous tasks for market ingestion, strategy evaluation, execution, and broadcasting.
- Paper simulator with configurable maker/taker fees and risk checks (per-trade cap, per-symbol exposure, drawdown kill switch).
- Kraken adapter (WebSocket + REST scaffold) plus a stub adapter for future stock integrations.
- Rolling EMA slope estimator feeding a momentum strategy (MACD-style) with deterministic aggression tuning.
- React/Next.js dashboard showing live KPIs, equity chart, and recent trades with paper/live mode toggle and aggression slider.
- SQLite persistence for fills and aggression changes.
- Structured logging via `structlog`, strict typing, and comprehensive unit tests.

## Architecture Overview

```
+-----------------------------+        +---------------------------+
|  Frontend (Next.js, SWR)    | <----> | FastAPI REST & WebSocket  |
|  - KPIs / Equity Chart      |        |  /api/* + /ws/stream      |
|  - Mode & Aggression        |        +------------+--------------+
+-----------------------------+                     |
                                                    |
                                         +----------v-----------+
                                         | Engine Runtime       |
                                         | - EngineClock        |
                                         | - MarketDataEngine   |
                                         | - StrategyEngine     |
                                         | - PaperSimulator     |
                                         | - RiskManager        |
                                         +----------+-----------+
                                                    |
                               +--------------------+--------------------+
                               |                                         |
                    +----------v---------+                  +------------v-------------+
                    | Persistence (SQL)  |                  | Adapters (Kraken, Stocks) |
                    | - Trades / Settings|                  | - WS + REST scaffolding   |
                    +--------------------+                  +---------------------------+
```

## Aggression Mapping

| Level | Position Fraction | Order Type | Stop Distance | Take Profit | Hold (s) | Cooldown (s) | Signal Threshold |
|-------|------------------:|------------|---------------|-------------|----------|--------------|------------------|
| 1     | 5%                | Limit      | 1.0%          | 0.3%        | 60       | 2            | 0.60             |
| 5     | ~23%              | Limit      | ~0.6%         | ~1.1%       | ~38      | ~13          | ~0.42            |
| 10    | 40%               | Market     | 0.2%          | 2.0%        | 5        | 30           | 0.20             |

Use the slider in the dashboard or `POST /api/settings/aggression?aggression=N` to adjust. Parameters are deterministic for reproducibility.

## Getting Started

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `BACKEND_URL` to point the dashboard to the backend host (defaults to `http://localhost:8000`).

### Combined Smoke Test

The root `Makefile` ships with a helper to run both sides sequentially:

```bash
make dev
```

This invokes `scripts/smoke.py`, which spins up the backend briefly and ensures the frontend can build.

## API Surface

- `GET /api/assets` — active symbols and descriptions.
- `GET /api/history/{symbol}` — recent price ticks retained in memory.
- `GET /api/orders` — _reserved for future use_.
- `GET /api/settings` — current mode and aggression parameters.
- `POST /api/mode` — toggle paper/live mode (live requires `{ "confirm": true }`).
- `POST /api/settings/aggression?aggression=N` — update aggression level.
- `GET /api/stats` — aggregate KPIs (PnL, win rate, fees, trades, cash, equity).
- WebSocket `/ws/stream` — streams `trade`, `portfolio:update`, and `stats:update` messages with bounded queues.

## Prediction & Strategy

The default strategy uses a rolling EMA slope estimator to gauge short-term momentum. Signals above/below a deterministic threshold map to LONG/SHORT actions. MACD-style components are provided under `engine/strategies/macd_rsi.py` for experimentation.

## Extending to Stocks

A stub `StocksAdapter` is included under `backend/crippel/adapters/stocks_stub.py`. Implement its `connect_market_data`, `submit_order`, and `close` methods to onboard a stock broker. Risk checks and runtime wiring already expect an `ExchangeAdapter` implementation, so the integration is isolated to the adapter.

## Testing & Quality

```bash
cd backend
pytest -q
mypy crippel
ruff check crippel
```

PyTest is configured with coverage reporting, and strict MyPy settings keep the codebase typed.

## Configuration & Secrets

- Copy `.env.example` to `.env` and populate Kraken API credentials for live trading.
- Settings are powered by `pydantic-settings` (`CRIPPEL_*` environment variables).
- All randomness is seeded for deterministic paper simulation runs.

## License

MIT — see [LICENSE](LICENSE).
