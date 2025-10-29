# 🐊 Croc-Bot — Autonomous Trading Desk

Croc-Bot is a production-grade Python trading stack that combines algorithmic execution, AI-assisted strategy research, rigorous risk management, and rich dashboards. The codebase now ships with Windows-first dependency profiles and PowerShell automation so the complete platform can be launched from a fresh workstation in minutes.

---

## 📚 Table of Contents
1. [Overview](#overview)
2. [Key Capabilities](#key-capabilities)
3. [System Architecture](#system-architecture)
4. [Supported Platforms](#supported-platforms)
5. [Prerequisites](#prerequisites)
6. [Windows PowerShell Quick Start](#windows-powershell-quick-start)
7. [Cross-Platform Quick Start](#cross-platform-quick-start)
8. [Running the Services](#running-the-services)
9. [Configuration](#configuration)
10. [Dashboards](#dashboards)
11. [Testing & Quality](#testing--quality)
12. [Project Layout](#project-layout)
13. [Troubleshooting](#troubleshooting)
14. [Support & Next Steps](#support--next-steps)

---

## Overview
- **Purpose:** Automated crypto and equities trading across paper and live venues with institutional-grade safety rails.
- **Core Stack:** FastAPI backend, async Kraken market adapter, Streamlit dashboards, optional AI co-pilot via LM Studio.
- **Operational Focus:** Smooth Windows/PowerShell experience with virtual environments and reproducible dependency sets.

## Key Capabilities
| Area | Highlights |
| --- | --- |
| **Market Connectivity** | Kraken WebSocket feed with crypto + xStocks coverage, async REST client for reference data. |
| **Execution Engines** | Paper simulator and live trading engine with slippage, fee, and market-hours models. |
| **Risk Controls** | Dynamic aggression ladder, drawdown guards, portfolio exposure caps, Discord alerting. |
| **Strategy Layer** | Multi-strategy manager (RSI, MACD, momentum, arbitrage, market making) plus AI-assisted signal generation. |
| **Monitoring** | ORJSON-powered FastAPI API, Streamlit dashboards, WebSocket streaming, structured logs. |

## System Architecture
```
🐊 Croc-Bot Trading Platform
├── FastAPI backend (uvicorn) with ORJSON responses
├── Market data adapter (Kraken WebSocket + REST)
├── Strategy manager (paper & live engines, AI assistant)
├── Risk manager (dynamic limits + Discord notifications)
├── Persistence layer (async SQLite repository)
├── Real trading dashboard (Streamlit + Plotly)
└── Simple HTML dashboard (standalone HTTP server)
```

## Supported Platforms
- ✅ **Windows 10/11** (PowerShell 7+, Python 3.11) — primary target.
- ✅ **macOS / Linux** — supported; install optional `crippel-trader[unix]` extras for uvloop/watchfiles performance boosters.

## Prerequisites
- Python **3.11 or newer** on PATH.
- Git (optional but recommended).
- For live trading: funded Kraken account + API keys.
- Optional: Discord webhook for alert streaming.

---

## Windows PowerShell Quick Start
```powershell
# 1. Clone the repository
git clone https://github.com/aaronwins356/Croc-Bot.git
cd Croc-Bot

# 2. Provision dependencies (installs backend + dashboards)
powershell -ExecutionPolicy Bypass -File crippel-trader\scripts\setup.ps1

# 3. Launch everything (backend, trading engine, dashboards)
StartBot.bat
```
The setup script performs a `python -m pip install -r crippel-trader\requirements.txt`, ensuring Windows-safe wheels are used. Optional Unix-only packages are automatically skipped.

## Cross-Platform Quick Start
```bash
git clone https://github.com/aaronwins356/Croc-Bot.git
cd Croc-Bot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r crippel-trader/requirements.txt
python start_croc_bot.py  # launches FastAPI backend on http://localhost:8000
```
Install optional extras on Unix systems for additional performance:
```bash
python -m pip install "crippel-trader[unix]"  # uvloop + watchfiles
```

---

## Running the Services
| Service | Command | Purpose |
| --- | --- | --- |
| **Backend API** | `python start_croc_bot.py` | Bootstraps a dedicated virtual environment, installs requirements, and serves FastAPI via uvicorn. |
| **Real Trading Engine** | `python start_real_trading.py` | Starts live trading loop with confirmations, slippage model, and safety checks. |
| **Real Trading Dashboard** | `streamlit run real_trading_dashboard.py --server.port 12000` | Rich Streamlit UI with Plotly charts, manual trade controls, and live portfolio metrics. |
| **Simple Dashboard** | `python simple_dashboard.py` | Lightweight HTML dashboard showcasing simulated data (no dependencies beyond stdlib). |

Backends expose:
- REST API: `http://localhost:8000/api`
- API Docs: `http://localhost:8000/docs`
- WebSocket Stream: `ws://localhost:8000/ws/stream`

---

## Configuration
Create `crippel-trader/backend/.env` (or use environment variables) to customise behaviour:
```env
# Trading modes
CRIPPEL_TRADING_MODE=paper
CRIPPEL_INITIAL_CAPITAL=200.0
CRIPPEL_DEFAULT_AGGRESSION=3

# Kraken API keys for live trading
CRIPPEL_KRAKEN_API_KEY=your_key
CRIPPEL_KRAKEN_API_SECRET=your_secret
CRIPPEL_REAL_TRADING=0  # flip to 1 once live trading is authorised

# Discord notifications
CRIPPEL_DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
CRIPPEL_DISCORD_NOTIFICATIONS_ENABLED=true

# AI strategy assistant
CRIPPEL_LMSTUDIO_API_BASE=http://localhost:1234/v1
CRIPPEL_LMSTUDIO_MODEL=croc-bot
CRIPPEL_AI_STRATEGY_GENERATION_ENABLED=true
```
Key risk levels (can be adjusted via aggression slider):

| Aggression | Max Drawdown | Per-Trade Risk | Position Size | Profile |
| --- | --- | --- | --- | --- |
| 1 | 5% | 1% | 0.5× | Capital preservation |
| 3 | 15% | 3% | 1.0× | Balanced |
| 5 | 25% | 5% | 1.5× | Growth |
| 7 | 35% | 7% | 2.0× | Opportunistic |
| 10 | 50% | 20% | 3.0× | High-octane |

---

## Dashboards
### Real Trading Dashboard
- Uses **Streamlit**, **Pandas**, **Plotly**.
- Visualises equity curves, allocation, order books, manual trade input.
- Served locally on `http://localhost:12000` via `StartBot.bat` or the Streamlit command above.

### Simple Dashboard
- Pure Python/HTML server for environments without GUI dependencies.
- Provides simulated prices, portfolio stats, and system heartbeat at `http://localhost:8080` (default).

---

## Testing & Quality
| Check | Command |
| --- | --- |
| Unit & async tests | `pytest` (within `crippel-trader/backend`) |
| Type checking | `mypy crippel-trader/backend/crippel` |
| Linting | `ruff check crippel-trader/backend/crippel` |

> Development extras can be installed with `python -m pip install "crippel-trader[dev]"`.

---

## Project Layout
```
Croc-Bot/
├── StartBot.bat                     # Full Windows launch orchestrator
├── start_croc_bot.py                # Backend bootstrap (venv + uvicorn)
├── start_real_trading.py            # Live trading entrypoint
├── real_trading_dashboard.py        # Streamlit UI
├── simple_dashboard.py              # Self-contained HTML dashboard
├── crippel-trader/
│   ├── backend/
│   │   ├── crippel/                 # Application package
│   │   └── main.py                  # ASGI entrypoint
│   ├── scripts/setup.ps1            # Windows dependency bootstrapper
│   ├── requirements.txt             # Windows-friendly dependency set
│   └── pyproject.toml               # Package metadata & extras
└── test_system.py                   # High-level system smoke test
```

---

## Troubleshooting
| Symptom | Resolution |
| --- | --- |
| **`uvloop` build fails on Windows** | Safe to ignore — dependency is skipped automatically in `requirements.txt`. |
| **`ModuleNotFoundError` after StartBot** | Run `python -m pip install -r crippel-trader\requirements.txt` manually to inspect logs. |
| **Streamlit dashboard cannot connect** | Confirm backend is running on `http://localhost:8000` and firewall allows localhost traffic. |
| **Discord alerts not delivered** | Ensure webhook URL is correct and notifications are enabled (`CRIPPEL_DISCORD_NOTIFICATIONS_ENABLED=true`). |

---

## Support & Next Steps
- Configure `.env` for live trading only after validating paper performance.
- Use the aggression slider (1–10) to tune drawdown tolerance in production.
- Extend strategies under `crippel-trader/backend/crippel/strategies/` and register them in the `StrategyManager`.
- For contributions, open issues or pull requests describing enhancements or bug fixes.

Happy trading and stay safe! 🐊
