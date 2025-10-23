const path = require('path');
const fs = require('fs');
const express = require('express');
const cors = require('cors');
const expressWs = require('express-ws');
const MarketDataService = require('./backend/services/marketDataService');

const PORT = process.env.PORT || 4000;

const app = express();
const server = require('http').createServer(app);
expressWs(app, server);

const marketDataService = new MarketDataService();

app.use(cors());
app.use(express.json());

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/api/assets', (_req, res) => {
  res.json({ assets: marketDataService.assets });
});

app.get('/api/analytics', (_req, res) => {
  res.json(marketDataService.getAnalytics());
});

app.get('/api/portfolio', (_req, res) => {
  res.json(marketDataService.getPortfolio());
});

app.get('/api/orders', (_req, res) => {
  res.json({ trades: marketDataService.getOrders() });
});

app.get('/api/history/:symbol', (req, res) => {
  res.json({
    symbol: req.params.symbol,
    candles: marketDataService.getHistory(req.params.symbol)
  });
});

app.get('/api/strategy/log', (_req, res) => {
  res.json({ log: marketDataService.getStrategyLog() });
});

app.post('/api/orders', (req, res) => {
  try {
    const { symbol, quantity, price } = req.body;
    const trade = marketDataService.placeOrder({ symbol, quantity, price, reason: 'manual-order' });
    res.status(201).json(trade);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

app.ws('/ws/stream', (ws) => {
  const sendSnapshot = () => {
    ws.send(JSON.stringify({
      type: 'market:update',
      market: marketDataService.assets,
      analytics: marketDataService.getAnalytics(),
      portfolio: marketDataService.getPortfolio(),
      strategy: { log: marketDataService.getStrategyLog() }
    }));
  };

  sendSnapshot();

  const handleUpdate = (payload) => {
    if (ws.readyState === ws.OPEN) {
      ws.send(JSON.stringify(payload));
    }
  };

  marketDataService.on('update', handleUpdate);

  ws.on('close', () => {
    marketDataService.off('update', handleUpdate);
  });
});

if (process.env.NODE_ENV === 'production') {
  const distPath = path.join(__dirname, 'dist');
  if (fs.existsSync(distPath)) {
    app.use(express.static(distPath));
    app.get('*', (_req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }
}

let shuttingDown = false;
const gracefulShutdown = () => {
  if (shuttingDown) return;
  shuttingDown = true;
  console.log('Received shutdown signal, closing services...');
  marketDataService.shutdown();
  server.close(() => {
    process.exit(0);
  });
  setTimeout(() => process.exit(0), 1000).unref();
};

['SIGINT', 'SIGTERM'].forEach((signal) => {
  process.on(signal, gracefulShutdown);
});

server.listen(PORT, () => {
  console.log(`Crippel Trader backend listening on http://localhost:${PORT}`);
});
