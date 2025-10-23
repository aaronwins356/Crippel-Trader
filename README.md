# Crippel Trader v2.0

Crippel Trader v2.0 is a full-stack trading simulator that emulates an institutional quant workstation. All market data, analytics, and trades are synthetic and safe for local experimentation.

## Features

- **Node.js + Express 5 backend** with synthetic tick generation, MACD/RSI/EMA analytics, automated portfolio management, and WebSocket streaming.
- **React 18 dashboard** delivering real-time charts, alpha radar analytics, portfolio intelligence, and manual trade controls.
- **Event-driven strategy engine** combining MACD momentum and RSI mean reversion heuristics to route simulated orders.
- **WebSocket streaming API** broadcasting candles, analytics, portfolio metrics, and strategy logs to connected clients.
- **Unit tests** covering market data generation, strategy execution, and REST endpoint responses.

## Getting Started

### Prerequisites

- Node.js 20+
- npm 9+

### Installation

```bash
npm install
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

Execute the Jest test suite:

```bash
npm test
```

## Project Structure

```
crippel-trader/
├── backend/
│   ├── server.js
│   ├── data/
│   │   └── seedAssets.js
│   ├── services/
│   │   ├── MarketDataService.js
│   │   ├── PortfolioService.js
│   │   ├── StrategyService.js
│   │   └── WebSocketService.js
│   └── utils/
│       ├── indicators.js
│       └── logger.js
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
│   ├── test_api.js
│   ├── test_market.js
│   └── test_strategy.js
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

Crippel Trader operates entirely on synthetic data. It never connects to live exchanges, stores credentials, or manages real capital. The simulator is intended for educational and research purposes only.

## License

MIT © 2024 Crippel Trader Contributors
