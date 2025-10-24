# Croc-Bot Monorepo

Croc-Bot is a mono-repository that bundles the **Crippel Trader** execution stack and the
**Crippel-Firm** research and simulation environment. The two projects share a design
goal of deterministic, auditable automation for crypto markets, but they target
different workflows:

- **Crippel Trader** – a production-ready trading engine with live and paper execution,
  a FastAPI backend, and a Next.js dashboard.
- **Crippel-Firm** – an autonomous trading organization simulator that coordinates a
  manager brain with specialized worker bots for research, analysis, and execution.

This document consolidates the documentation that previously lived in the individual
project READMEs so that you have a single place to understand, build, and run every
component.

## Repository Layout

```
Croc-Bot/
├── crippel-trader/           # Trading engine (backend + dashboard)
│   ├── backend/              # FastAPI app, runtime, services, tests
│   ├── frontend/             # Next.js dashboard
│   ├── requirements.txt      # Backend dependencies
│   └── pyproject.toml        # Packaging configuration
├── crippel-firm/             # Autonomous firm simulator
│   ├── backend/              # Manager brain, bots, API, tests
│   ├── requirements.txt      # Simulation dependencies
│   └── pyproject.toml        # Packaging configuration
└── README.md                 # (This file) unified documentation
```

Each sub-project ships its own virtual environment/dependency metadata. Licenses are
kept alongside the projects (`crippel-trader/LICENSE` and `crippel-firm/LICENSE`).

## Crippel Trader

### Overview

Crippel Trader is a deterministic crypto trading stack that supports paper and live
execution, market prediction, and a live dashboard. It is designed for a single
operator with a focus on safety, reproducibility, and fast tick-to-signal
performance.

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

### Key Features

- FastAPI backend with asynchronous tasks for market ingestion, strategy evaluation,
  execution, and broadcasting.
- Paper simulator with configurable maker/taker fees and risk checks (per-trade cap,
  per-symbol exposure, drawdown kill switch).
- Kraken adapter (WebSocket + REST scaffold) plus a stub adapter for future stock
  integrations.
- Rolling EMA slope estimator feeding a momentum strategy (MACD-style) with
  deterministic aggression tuning.
- React/Next.js dashboard showing live KPIs, equity chart, and recent trades with
  paper/live mode toggle and aggression slider.
- SQLite persistence for fills and aggression changes.
- Structured logging via `structlog`, strict typing, and comprehensive unit tests.

### Getting Started (Backend)

```bash
cd crippel-trader/backend
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
uvicorn main:app --reload
```

Set `BACKEND_URL` in the frontend environment if the dashboard should talk to a remote
backend (defaults to `http://localhost:8000`).

### Getting Started (Frontend)

```bash
cd crippel-trader/frontend
npm install
npm run dev
```

### Operations & Quality Gates

- `make dev` (from `crippel-trader`) runs the backend and builds the frontend to perform
  a quick smoke test.
- Run the automated checks from the backend directory:
  ```bash
  cd crippel-trader/backend
  pytest -q
  mypy crippel
  ruff check crippel
  ```

## Crippel-Firm

### Overview

Crippel-Firm is an experimental autonomous trading organization composed of a manager
bot and a set of specialized worker bots. The manager hires, evaluates, and, when
needed, terminates worker bots based on performance and firm health. The provided
implementation focuses on deterministic simulation suitable for unit testing and offline
experimentation. Real trading integrations are abstracted behind adapters for
swap-in production implementations.

### Key Features

- Manager brain that tracks firm performance, hires/fires workers, and reallocates
  virtual capital.
- Event-driven architecture using an asyncio-based event bus.
- Worker bot implementations for research, analysis, trading, and risk management.
- Paper trading simulator and Kraken adapter stub for integration testing.
- FastAPI service exposing REST and WebSocket endpoints for monitoring and control.
- Test suite covering manager decisions, worker lifecycles, and research ingestion.

### Getting Started

```bash
cd crippel-firm
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m backend.main
```

The default configuration runs the firm in simulation mode and periodically evaluates
bot performance. Launch the optional API to reach REST endpoints at `http://127.0.0.1:8000`.

### Tests

From the `crippel-firm` directory run:

```bash
pytest
pytest-asyncio
pytest-cov
```

(Additional mocks use `respx`.)

## Working Across Projects

- Use isolated virtual environments per project; their Python requirements differ
  (`crippel-trader` targets Python 3.11 while `crippel-firm` targets Python 3.10+).
- Configuration for live trading is stored in environment variables; see the
  backend `.env.example` files where applicable.
- Both projects rely on FastAPI, so shared operational knowledge (uvicorn, dependency
  injection patterns, async services) transfers between them.

## License

Both `crippel-trader` and `crippel-firm` are distributed under the MIT license. Refer to
the license files in each project directory for details.
