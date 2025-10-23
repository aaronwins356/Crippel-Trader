import http from 'http';
import fs from 'fs';
import path from 'path';
import express from 'express';
import cors from 'cors';
import MarketDataService from './services/MarketDataService.js';
import WebSocketService from './services/WebSocketService.js';
import { logger } from './utils/logger.js';

const resolveDistPath = () => path.resolve(process.cwd(), 'dist');

export const createApp = ({ marketOptions } = {}) => {
  const app = express();
  const marketDataService = new MarketDataService(marketOptions);

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
    res.json({ symbol: req.params.symbol, candles: marketDataService.getHistory(req.params.symbol) });
  });

  app.get('/api/strategy/log', (_req, res) => {
    res.json({ log: marketDataService.getStrategyLog() });
  });

  app.post('/api/orders', (req, res, next) => {
    try {
      const { symbol, quantity, price } = req.body;
      if (!symbol || !Number.isFinite(Number(quantity))) {
        res.status(400).json({ error: 'symbol and quantity are required' });
        return;
      }
      const numericQuantity = Number(quantity);
      const numericPrice = price ? Number(price) : undefined;
      const trade = marketDataService.placeOrder({ symbol, quantity: numericQuantity, price: numericPrice, reason: 'manual-override', strategy: 'manual' });
      res.status(201).json(trade);
    } catch (error) {
      next(error);
    }
  });

  if (process.env.NODE_ENV === 'production') {
    const distPath = resolveDistPath();
    if (fs.existsSync(distPath)) {
      app.use(express.static(distPath));
      app.get('*', (_req, res) => {
        res.sendFile(path.join(distPath, 'index.html'));
      });
    }
  }

  app.use((err, _req, res, _next) => {
    logger.error('Unhandled server error', err);
    res.status(err.status || 500).json({ error: err.message || 'Internal Server Error' });
  });

  return { app, marketDataService };
};

export const createServer = async ({ port = Number(process.env.PORT || 4000), marketOptions } = {}) => {
  const { app, marketDataService } = createApp({ marketOptions });
  const server = http.createServer(app);
  const wsService = new WebSocketService({ server, marketDataService });

  const start = () => new Promise((resolve) => {
    server.listen(port, () => {
      logger.info(`Crippel Trader backend listening on http://localhost:${port}`);
      resolve();
    });
  });

  const stop = () => new Promise((resolve, reject) => {
    wsService.shutdown();
    marketDataService.shutdown();
    server.close((error) => {
      if (error) {
        logger.error('Error while closing server', error);
        reject(error);
        return;
      }
      resolve();
    });
  });

  return { app, server, start, stop, marketDataService, wsService };
};

if (process.env.NODE_ENV !== 'test') {
  const { start, stop } = await createServer();

  const gracefulShutdown = () => {
    logger.info('Received shutdown signal, closing Crippel Trader backend');
    stop().finally(() => process.exit(0));
  };

  ['SIGINT', 'SIGTERM'].forEach((signal) => {
    process.on(signal, gracefulShutdown);
  });

  start().catch((error) => {
    logger.error('Failed to start server', error);
    process.exit(1);
  });
}
