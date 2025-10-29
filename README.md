# 🐊 Croc-Bot: Professional Autonomous Trading System

**Croc-Bot** is a sophisticated, open-source Python trading bot designed to be a profitable autonomous trading firm. It features advanced AI strategy generation, comprehensive risk management, and a professional dashboard accessible via localhost.

## 🌟 Key Features

### 🤖 **Autonomous Trading Intelligence**
- **AI Strategy Generation**: Self-improving algorithms that create and optimize new trading strategies
- **Multi-Strategy Execution**: RSI, MACD, Momentum, Bollinger Bands, Arbitrage, and Market Making
- **Dynamic Strategy Rebalancing**: Automatic weight adjustment based on performance

### 📊 **Professional Dashboard**
- **Real-time Portfolio Tracking**: Live P&L, equity curves, and position monitoring
- **Risk Management Interface**: Aggression slider (1-10) with dynamic risk controls
- **Strategy Performance Analytics**: Win rates, Sharpe ratios, and drawdown analysis
- **Trade History & Analytics**: Comprehensive trade logging and performance metrics

### 🛡️ **Advanced Risk Management**
- **Dynamic Risk Limits**: Automatically adjusted based on aggression level
- **Portfolio VaR Calculation**: Value-at-Risk monitoring with real-time alerts
- **Drawdown Protection**: Automatic position closure on excessive losses
- **Position Size Management**: Intelligent sizing based on volatility and correlation

### 💰 **Multi-Asset Trading**
- **Cryptocurrency Support**: BTC, ETH, ADA, SOL, MATIC, DOT, LINK, UNI, AAVE, ATOM
- **Stock Trading**: TSLA, AAPL, GOOGL, MSFT, AMZN, NVDA, META, SPY, QQQ, and more
- **Real-time Market Data**: Live Kraken WebSocket integration
- **Paper Trading Mode**: Risk-free testing with real market data

### 🔔 **Smart Notifications**
- **Discord Integration**: Real-time trade alerts and performance updates
- **Risk Alerts**: Immediate notifications for risk threshold breaches
- **System Status Updates**: Startup, shutdown, and error notifications

### 🎯 **Trading Modes**
- **Paper Trading**: Start with $200 virtual capital, scale to $5K+ with proof of concept
- **Live Trading**: Seamless transition to real money trading (Kraken integration)
- **Aggression Control**: 1-10 slider controlling risk appetite and position sizing

## 🚀 Quick Start

### 1. **Clone and Setup**
```bash
git clone https://github.com/aaronwins356/Croc-Bot.git
cd Croc-Bot
```

### 2. **Run the System**
```bash
# Simple one-command startup
python start_croc_bot.py
```

### 3. **Access the Dashboard**
- **API Documentation**: http://localhost:8000/docs
- **WebSocket Stream**: ws://localhost:8000/ws/stream
- **System Status**: http://localhost:8000/status

### 4. **Test the System**
```bash
# Run comprehensive system tests
python test_system.py
```

## 🏗️ Architecture Overview

```
🐊 Croc-Bot Trading System
├── 📊 Real-time Market Data (Kraken WebSocket)
├── 🧠 Strategy Manager (10+ Trading Strategies)
├── 🛡️  Risk Manager (Dynamic Risk Controls)
├── 💰 Paper Trading Engine (Virtual Portfolio)
├── 🔔 Discord Notifications (Trade Alerts)
├── 📈 Professional Dashboard (React + FastAPI)
└── 🤖 AI Strategy Generator (Self-Improving)
```

## 📁 Project Structure

```
Croc-Bot/
├── crippel-trader/                 # Main trading system
│   ├── backend/                    # FastAPI backend
│   │   ├── crippel/
│   │   │   ├── strategies/         # Trading strategies
│   │   │   ├── adapters/           # Exchange adapters
│   │   │   ├── models/             # Data models
│   │   │   ├── paper_trading.py    # Paper trading engine
│   │   │   ├── risk_manager.py     # Risk management
│   │   │   ├── strategy_manager.py # Strategy coordination
│   │   │   ├── notifications.py    # Discord integration
│   │   │   └── enhanced_runtime.py # System orchestration
│   │   └── requirements.txt        # Python dependencies
│   └── frontend/                   # Next.js dashboard (future)
├── start_croc_bot.py              # Easy startup script
├── test_system.py                 # System verification
└── README.md                      # This file
```

## 🎛️ Configuration & Settings

### **Environment Variables**
Create a `.env` file in `crippel-trader/backend/` for custom configuration:

```bash
# Trading Configuration
CRIPPEL_TRADING_MODE=paper                    # paper or live
CRIPPEL_INITIAL_CAPITAL=200.0                 # Starting capital
CRIPPEL_DEFAULT_AGGRESSION=3                  # Risk level (1-10)

# API Keys (for live trading)
CRIPPEL_KRAKEN_API_KEY=your_kraken_api_key
CRIPPEL_KRAKEN_API_SECRET=your_kraken_secret

# Discord Notifications
CRIPPEL_DISCORD_WEBHOOK_URL=your_discord_webhook
CRIPPEL_DISCORD_NOTIFICATIONS_ENABLED=true

# AI Strategy Generation
CRIPPEL_OPENAI_API_KEY=your_openai_key
CRIPPEL_AI_STRATEGY_GENERATION_ENABLED=true
```

### **Risk Management Levels**

| Aggression | Max Drawdown | Per-Trade Risk | Position Size | Description |
|------------|--------------|----------------|---------------|-------------|
| 1 (Conservative) | 5% | 1% | 0.5x | Ultra-safe, minimal risk |
| 3 (Moderate) | 15% | 3% | 1.0x | Balanced approach |
| 5 (Balanced) | 25% | 5% | 1.5x | Standard trading |
| 7 (Aggressive) | 35% | 7% | 2.0x | Higher risk/reward |
| 10 (Maximum) | 50% | 20% | 3.0x | Maximum aggression |

## 📊 API Endpoints

### **Portfolio & Performance**
- `GET /api/portfolio` - Current portfolio state
- `GET /api/performance` - Performance metrics
- `GET /api/equity-curve` - Equity curve data for charts

### **Trading & Orders**
- `GET /api/orders` - Open orders
- `POST /api/orders` - Submit manual order
- `DELETE /api/orders/{id}` - Cancel order
- `GET /api/trades` - Trade history

### **Strategy Management**
- `GET /api/strategies` - Strategy performance
- `POST /api/strategies/{name}/activate` - Activate strategy
- `POST /api/strategies/{name}/deactivate` - Deactivate strategy

### **Risk & Settings**
- `GET /api/risk` - Risk metrics
- `POST /api/settings/aggression` - Set aggression level
- `POST /api/settings/mode` - Change trading mode

### **System Status**
- `GET /api/status` - System status
- `GET /api/health` - Health check
- `GET /api/assets` - Available trading assets

## 🧠 Trading Strategies

### **Technical Analysis**
- **RSI Strategy**: Mean reversion based on Relative Strength Index
- **MACD Strategy**: Trend following with MACD crossovers
- **Momentum Strategy**: Multi-timeframe momentum detection
- **Bollinger Bands**: Mean reversion and breakout detection
- **Multi-Timeframe**: Trend alignment across timeframes

### **Arbitrage**
- **Statistical Arbitrage**: Pair trading based on correlation
- **Cross-Exchange**: Price discrepancy exploitation
- **Triangular Arbitrage**: Currency triplet opportunities

### **Market Making**
- **Basic Market Making**: Dynamic spread-based liquidity provision
- **Adaptive Market Making**: ML-enhanced market making with learning

## 🔧 Development & Testing

### **Manual Testing**
```bash
# Test system components
python test_system.py

# Run backend directly
cd crippel-trader/backend
uvicorn crippel.app:app --reload --host 0.0.0.0 --port 8000
```

### **API Testing**
```bash
# Test API endpoints
curl http://localhost:8000/api/status
curl http://localhost:8000/api/portfolio
curl http://localhost:8000/api/performance
```

### **WebSocket Testing**
```javascript
// Connect to real-time data stream
const ws = new WebSocket('ws://localhost:8000/ws/stream');
ws.onmessage = (event) => console.log(JSON.parse(event.data));
```

## 🗺️ Repository Mapping Utilities

Generate architectural summaries and dependency reports for the repository with
the bundled mapper:

```bash
python tools/repo_mapper.py . --output analysis
```

The command writes Markdown, CSV, JSON, and Graphviz artefacts into the
`analysis/` directory capturing module boundaries, dependencies, and file-level
metrics. Regenerate the reports after significant code changes to keep them up
to date.

## 🚨 Important Notes

### **Paper Trading Mode**
- ✅ **Safe**: No real money at risk
- ✅ **Real Data**: Uses live Kraken market data
- ✅ **Full Features**: All strategies and risk management active
- ✅ **No API Keys**: Works without exchange credentials

### **Live Trading Mode**
- ⚠️ **Real Money**: Actual trading with real capital
- ⚠️ **API Keys Required**: Kraken API credentials needed
- ⚠️ **Confirmation Required**: Must explicitly confirm live mode
- ⚠️ **Start Small**: Begin with minimal capital

### **Discord Notifications**
Your Discord webhook is pre-configured for:
- 🔔 Trade execution alerts
- 📊 Performance updates
- 🚨 Risk management alerts
- ⚙️ System status updates

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE files for details.

## ⚠️ Disclaimer

**This software is for educational and research purposes. Trading involves substantial risk of loss. Past performance does not guarantee future results. Use at your own risk.**

---

**🐊 Happy Trading with Croc-Bot!** 

*Built with ❤️ for the trading community*
