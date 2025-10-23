# Crippel Trader

Crippel Trader is a self-contained automated trading laboratory that simulates a multi-asset execution engine and renders a professional, quant-grade analytics surface. The backend produces synthetic yet realistic tick data, drives a systematic strategy, and exposes a WebSocket stream alongside a REST API. The React-based frontend consumes the live feed and visualizes market structure, portfolio risk, and strategy telemetry with a sleek institutional design.

## Architecture

- **Backend** – Node.js/Express server (`server.js`) backed by a `MarketDataService`. It continuously generates candles for cryptocurrencies, equities, and macro instruments, applies technical indicators, and runs an event-driven strategy through a shared `PortfolioService`. Results are available over:
  - `GET /api/assets`, `GET /api/analytics`, `GET /api/portfolio`, `GET /api/orders`, and `GET /api/history/:symbol`
  - `POST /api/orders` for manual overrides
  - `ws://<host>/ws/stream` for high-frequency updates (market, analytics, portfolio, and strategy log)
- **Frontend** – React application bundled with Webpack (`src/`). The dashboard showcases:
  - Real-time price action for the selected asset with indicator telemetry
  - Leader/laggard dispersion heat map
  - Portfolio allocation pie, leverage gauges, and momentum vs RSI monitor
  - Execution blotter and strategy timeline styled for an institutional command center

## Getting Started

```bash
npm install
npm run dev
```

The development script launches the Express server on **http://localhost:4000** and Webpack in watch mode. Visit **http://localhost:3000** to interact with the dashboard (the dev server proxies API and WebSocket requests).

For a production build:

```bash
npm run build
npm start
```

The `build` command emits static assets to `dist/`. `npm start` serves both the API and the precompiled frontend.

## Manual Trading Overrides

Submit manual orders via the REST API using JSON payloads:

```bash
curl -X POST http://localhost:4000/api/orders \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTC-USD","quantity":2,"price":41000}'
```

Positive quantity represents a buy, negative quantity a sell. The execution is validated against cash availability and feeds directly into the portfolio state and real-time stream.

## Folder Structure

```
backend/
  data/seedAssets.js         # Instrument universe
  services/                  # Market generator, portfolio engine, strategy
  utils/                     # Technical indicator math
src/
  components/                # UI building blocks
  hooks/useTradingStream.js  # WebSocket abstraction
  utils/format.js            # Formatting helpers
  App.js                     # Dashboard layout
  index.js / index.html      # Entry point
  styles.css                 # Quant aesthetic theme
```

## Disclaimer

Crippel Trader is a fully synthetic environment designed for demonstration and educational purposes. It **does not** connect to live markets nor execute real trades.
