# 🐊 Croc-Bot Trading System

**Professional autonomous trading system with AI strategy generation, real-time market data, and comprehensive risk management.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## 🚀 Features

- **📊 Paper & Live Trading Modes** - Safe paper trading with real market data, or live trading with real money
- **🔐 Safety First** - Multi-layer safety checks, explicit confirmations, and countdown for live trading
- **💹 Real-Time Market Data** - Kraken WebSocket integration for crypto and xStocks (tokenized equities)
- **🤖 AI Strategy Generation** - Offline local LLM-powered strategy creation and optimization
- **⚡ High-Performance** - Async architecture with sub-second tick processing
- **📈 Risk Management** - Dynamic position sizing, drawdown limits, and exposure controls
- **🔔 Discord Notifications** - Real-time alerts for trades, performance, and system events
- **🎯 Multi-Asset Support** - Trade crypto (BTC, ETH, etc.) and xStocks (TSLA, AAPL, SPY, etc.)
- **📱 Modern Dashboard** - React-based real-time trading dashboard

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Trading Modes](#-trading-modes)
- [Supported Assets](#-supported-assets)
- [Architecture](#-architecture)
- [Development](#-development)
- [Safety & Risk Management](#-safety--risk-management)
- [API Documentation](#-api-documentation)
- [Troubleshooting](#-troubleshooting)

---

## ⚡ Quick Start

### Windows

```powershell
# Install dependencies
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run backend (paper trading mode by default)
cd backend
uvicorn crippel.app:app --reload
```

### Linux/macOS

```bash
# Install dependencies
bash scripts/setup.sh

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run backend (paper trading mode by default)
cd backend
uvicorn crippel.app:app --reload
```

### Using Make Commands

```bash
# See all available commands
make help

# Run backend in development mode
make run-dev

# Run linter
make lint

# Run tests
make test
```

**Windows users**: Use `powershell .\make.ps1 <command>` instead of `make`.

---

## 📦 Installation

### Prerequisites

- **Python 3.11+** (3.11, 3.12 recommended)
- **pip** and **virtualenv**
- **(Optional)** Node.js 18+ for frontend dashboard
- **(Optional)** PostgreSQL for persistence

### Automated Setup

**Windows:**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

**Linux/macOS:**
```bash
bash scripts/setup.sh
```

### Manual Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip and tools
python -m pip install --upgrade pip wheel setuptools

# Install dependencies
pip install -r requirements.txt

# Optional: Install platform-specific optimizations
# Linux/macOS only:
pip install uvloop>=0.19

# Optional: Install TA-Lib for technical analysis
# Requires TA-Lib C library first
# Ubuntu/Debian: sudo apt-get install ta-lib
# macOS: brew install ta-lib
pip install TA-Lib>=0.4.28
```

---

## ⚙️ Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Key Configuration Options

#### Trading Mode & Safety

```bash
# Paper trading (default) - safe for testing
CRIPPEL_TRADING_MODE=paper
CRIPPEL_REAL_TRADING=0

# Live trading - REAL MONEY
# CRIPPEL_TRADING_MODE=real
# CRIPPEL_REAL_TRADING=1  # MUST be 1 for live trading
```

#### Kraken API Credentials

```bash
# Get from: https://www.kraken.com/u/security/api
CRIPPEL_KRAKEN_API_KEY=your_api_key_here
CRIPPEL_KRAKEN_API_SECRET=your_api_secret_here
```

#### Capital & Risk

```bash
CRIPPEL_INITIAL_CAPITAL=200.0
CRIPPEL_MAX_CAPITAL=5000.0
CRIPPEL_DEFAULT_AGGRESSION=3  # 1-10 scale
```

#### Discord Notifications

```bash
CRIPPEL_DISCORD_NOTIFICATIONS_ENABLED=true
CRIPPEL_DISCORD_WEBHOOK_URL=your_webhook_url
```

See `.env.example` for all available options.

---

## 🎯 Trading Modes

### Paper Trading (Default)

**Safe simulation mode with real market data:**

- ✅ Uses real Kraken WebSocket market data
- ✅ Executes trades with 100% real trading logic
- ✅ No real money at risk
- ✅ Perfect for testing strategies and learning
- ✅ Default mode - no API keys required for testing

**Configuration:**
```bash
CRIPPEL_TRADING_MODE=paper
CRIPPEL_REAL_TRADING=0
```

### Live Trading

**Real money trading on Kraken exchange:**

- ⚠️ **Real money at risk**
- ⚠️ Requires both flags: `trading_mode=real` AND `real_trading=1`
- ⚠️ Requires valid Kraken API credentials
- ⚠️ 10-second countdown on startup (can cancel with Ctrl+C)
- ⚠️ Prominent warning banner

**Configuration:**
```bash
CRIPPEL_TRADING_MODE=real
CRIPPEL_REAL_TRADING=1
CRIPPEL_KRAKEN_API_KEY=<your_key>
CRIPPEL_KRAKEN_API_SECRET=<your_secret>
```

**Safety Features:**

1. **Dual Confirmation**: Requires both `trading_mode=real` AND `real_trading=1`
2. **Credential Validation**: Checks for valid API keys before startup
3. **Startup Countdown**: 10-second warning with cancel option
4. **Prominent Banner**: Clear visual warning in terminal
5. **Comprehensive Logging**: All trades and decisions logged

---

## 💰 Supported Assets

### Cryptocurrencies

Kraken crypto pairs (automatically converted to Kraken format):

- **BTC/USD** - Bitcoin (XBT/USD on Kraken)
- **ETH/USD** - Ethereum
- **ADA/USD** - Cardano
- **SOL/USD** - Solana
- **MATIC/USD** - Polygon
- **DOT/USD** - Polkadot
- **LINK/USD** - Chainlink
- **UNI/USD** - Uniswap
- **AAVE/USD** - Aave
- **ATOM/USD** - Cosmos

### Kraken xStocks (Tokenized Stocks)

SPL tokens on Solana blockchain, tradable 24/5:

**Individual Stocks:**
- **TSLA** - Tesla (TSLAx/USD)
- **AAPL** - Apple (AAPLx/USD)
- **GOOGL** - Google (GOOGLx/USD)
- **MSFT** - Microsoft (MSFTx/USD)
- **AMZN** - Amazon (AMZNx/USD)
- **NVDA** - NVIDIA (NVDAx/USD)
- **META** - Meta (METAx/USD)

**ETFs:**
- **SPY** - S&P 500 (SPYx/USD)
- **QQQ** - Nasdaq 100 (QQQx/USD)
- **IWM** - Russell 2000 (IWMx/USD)
- **GLD** - Gold (GLDx/USD)
- **TLT** - Treasury Bonds (TLTx/USD)

**Symbol Routing:** The system automatically converts symbols to Kraken format (e.g., `TSLA` → `TSLAx/USD`, `BTC/USD` → `XBT/USD`).

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Croc-Bot Trading System                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   FastAPI    │  │   WebSocket  │  │  REST API       │   │
│  │   Backend    │←→│   Manager    │←→│  Endpoints      │   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
│         ↕                 ↕                    ↕              │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   Trading    │  │     Risk     │  │   Strategy      │   │
│  │   Engine     │←→│   Manager    │←→│   Manager       │   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
│         ↕                                      ↕              │
│  ┌──────────────┐                    ┌─────────────────┐   │
│  │   Kraken     │                    │      AI         │   │
│  │   Adapter    │                    │   Generator     │   │
│  └──────────────┘                    └─────────────────┘   │
│         ↕                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │          Kraken WebSocket (Market Data)              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Key Modules

- **`crippel/app.py`** - FastAPI application factory
- **`crippel/config.py`** - Centralized configuration with pydantic-settings
- **`crippel/adapters/kraken.py`** - Kraken exchange integration
- **`crippel/paper_trading.py`** - Paper trading engine
- **`crippel/real_trading_engine.py`** - Live trading engine
- **`crippel/risk_manager.py`** - Risk management and position sizing
- **`crippel/strategy_manager.py`** - Strategy orchestration
- **`crippel/notifications.py`** - Discord alert system
- **`crippel/ws.py`** - WebSocket connection manager
- **`crippel/safety.py`** - Startup safety checks

---

## 🛠️ Development

### Available Commands

```bash
# Show help
make help

# Install dependencies
bash scripts/setup.sh  # Linux/macOS
powershell scripts\setup.ps1  # Windows

# Run backend (development mode with hot reload)
make run-dev

# Run linter
make lint

# Format code
make format

# Type checking
make typecheck

# Run tests
make test

# Clean temporary files
make clean
```

### Code Quality

The project uses modern Python tooling:

- **Ruff** - Fast Python linter and formatter
- **Black** - Code formatting (via ruff)
- **mypy** - Static type checking (strict mode)
- **pytest** - Testing framework

### Testing

```bash
# Run all tests
make test

# Run specific test file
cd backend && pytest tests/test_adapters.py -v

# With coverage report
cd backend && pytest --cov=crippel --cov-report=html
```

---

## 🛡️ Safety & Risk Management

### Multi-Layer Safety System

1. **Default Paper Trading** - Safe mode by default
2. **Dual Confirmation** - Two flags required for live trading
3. **Credential Validation** - API keys checked before startup
4. **Startup Countdown** - 10-second warning with cancel option
5. **Dynamic Risk Limits** - Adjust based on aggression level

### Risk Parameters (Aggression-Scaled)

| Aggression | Drawdown Limit | Per-Trade Cap | Position Size |
|------------|----------------|---------------|---------------|
| 1 (Conservative) | 5% | 1% | 0.5x |
| 3 (Moderate) | 15% | 5% | 1.0x |
| 5 (Balanced) | 25% | 10% | 1.5x |
| 7 (Aggressive) | 35% | 15% | 2.0x |
| 10 (Maximum) | 50% | 20% | 3.0x |

**Risk Controls:**
- Maximum drawdown limits
- Per-trade capital caps
- Per-symbol exposure limits
- Position concentration monitoring
- Automatic circuit breakers

---

## 📚 API Documentation

### Interactive Documentation

Start the backend and visit:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

```
GET  /                     - System information
GET  /api/health           - Health check
GET  /api/healthz          - Kubernetes health check
GET  /api/readyz           - Readiness check
GET  /api/portfolio        - Portfolio state
GET  /api/performance      - Performance metrics
GET  /api/strategies       - Active strategies
GET  /api/risk             - Risk summary
POST /api/orders           - Submit order
GET  /api/status           - System status
WS   /ws/stream            - Real-time data stream
```

---

## 🐛 Troubleshooting

### Common Issues

#### Backend won't start

```bash
# Check Python version
python --version  # Should be 3.11+

# Reinstall dependencies
bash scripts/setup.sh

# Check for errors
uvicorn crippel.app:app --log-level debug
```

#### WebSocket connection issues

- Check firewall settings
- Verify Kraken API is accessible
- Ensure no proxy blocking WebSocket connections

#### "uvloop not found" on Windows

This is **normal and safe**. uvloop is a Linux/macOS optimization not available on Windows. The system works fine without it.

#### "ta-lib not found"

TA-Lib is optional. The system works without it. To install:

**Windows**: Download wheel from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib)
**Linux**: `sudo apt-get install ta-lib && pip install TA-Lib`
**macOS**: `brew install ta-lib && pip install TA-Lib`

### Getting Help

- Check logs in `/var/log/` (if using systemd)
- Enable debug logging: `--log-level debug`
- Review configuration: `.env` file
- Check [GitHub Issues](https://github.com/your-repo/issues)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

**Trading involves substantial risk of loss. This software is provided "as is" without warranty of any kind.**

- Past performance does not guarantee future results
- Only trade with money you can afford to lose
- Test thoroughly in paper trading mode before live trading
- Understand all risks before trading with real money
- The authors are not responsible for financial losses

---

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Market data from [Kraken](https://www.kraken.com/)
- AI powered by [llama.cpp](https://github.com/ggerganov/llama.cpp) or local [Transformers](https://huggingface.co/docs/transformers/index)
- Inspired by professional trading systems

---

**Happy Trading! 🚀📈**
