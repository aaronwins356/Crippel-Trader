# Crippel-Trader

Crippel-Trader is a full-stack trading simulator that emulates an institutional quant workstation. All market data, analytics, and trades are synthetic and safe for local experimentation.

## Repository

Clone the latest code straight from the official GitHub repository:

```bash
git clone https://github.com/CrippelHQ/Crippel-Trader.git
cd Crippel-Trader
```

Windows users can launch the full development environment with the bundled [`startTrading.bat`](startTrading.bat) script after cloning. The script installs dependencies on first run and opens both the Python backend and React frontend consoles.

## Features

- **Python FastAPI backend** powering synthetic tick generation, MACD/RSI/EMA analytics, automated portfolio management, and WebSocket streaming.
- **React 18 dashboard** delivering real-time charts, alpha radar analytics, portfolio intelligence, and manual trade controls.
- **Event-driven strategy engine** combining MACD momentum and RSI mean reversion heuristics to route simulated orders.
- **WebSocket streaming API** broadcasting candles, analytics, portfolio metrics, and strategy logs to connected clients.
- **Unit tests** covering market data generation, strategy execution, and REST endpoint responses.

## Getting Started

### Prerequisites

- Node.js 20+
- npm 9+
- Python 3.11+

Install JavaScript and Python dependencies:

```bash
npm install
python -m pip install -r requirements.txt
```

### Development Mode

Run backend (port 4000) and frontend (port 3000) concurrently:

```bash
npm run dev
```

The dashboard is available at [http://localhost:3000](http://localhost:3000) with live data sourced from the local backend at port 4000.

### Production Build

Generate an optimized frontend bundle and start the backend in production mode:

```bash
npm run build
npm start
```

### Testing

Execute the Python test suite:

```bash
npm test
```

## Project Structure

```
crippel-trader/
├── pybackend/
│   ├── server.py
│   ├── data/
│   │   └── seed_assets.py
│   ├── services/
│   │   ├── market_data.py
│   │   ├── portfolio.py
│   │   ├── strategy.py
│   │   ├── live_trading.py
│   │   └── websocket_manager.py
│   └── utils/
│       ├── indicators.py
│       └── logger.py
├── src/
│   ├── components/
│   │   ├── AnalyticsPanel.jsx
│   │   ├── ChartPanel.jsx
│   │   ├── HeaderBar.jsx
│   │   ├── PortfolioPanel.jsx
│   │   └── TradeControls.jsx
│   ├── hooks/useTradingStream.js
│   ├── utils/format.js
│   ├── App.js
│   ├── index.js
│   ├── index.html
│   └── styles.css
├── tests/
│   ├── test_api.py
│   ├── test_market.py
│   └── test_strategy.py
├── requirements.txt
├── package.json
├── webpack.config.js
├── .env.example
├── README.md
└── ...
```

## API Overview

### REST

- `GET /api/assets` — list of tracked assets and current prices.
- `GET /api/analytics` — full indicator suite for each asset.
- `GET /api/portfolio` — portfolio state, positions, and risk metrics.
- `GET /api/orders` — recent trades executed by the system or manually.
- `GET /api/history/:symbol` — recent candle history for the requested symbol.
- `POST /api/orders` — manual order override `{ symbol, quantity, price? }`.

### WebSocket

- `ws://localhost:4000/ws/stream` — pushes `market:update` payloads with market data, analytics, portfolio metrics, and strategy logs, plus `strategy:trade` events on execution.

## Security & Ethics

Crippel-Trader operates entirely on synthetic data. It never connects to live exchanges, stores credentials, or manages real capital. The simulator is intended for educational and research purposes only.

## License

MIT © 2024 Crippel-Trader Contributors
