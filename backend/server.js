import http from 'http';
import fs from 'fs';
import path from 'path';
import express from 'express';
import cors from 'cors';
import MarketDataService from './services/MarketDataService.js';
import LiveTradingService from './services/LiveTradingService.js';
import TradingModeService from './services/TradingModeService.js';
import WebSocketService from './services/WebSocketService.js';
import { logger } from './utils/logger.js';

const resolveDistPath = () => path.resolve(process.cwd(), 'dist');

export const createApp = ({ marketOptions } = {}) => {
  const app = express();
  const marketDataService = new MarketDataService(marketOptions);
  const liveTradingService = new LiveTradingService();
  const tradingModeService = new TradingModeService({ marketDataService, liveTradingService });

  app.use(cors());
  app.use(express.json());

  app.get('/health', (_req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
  });

  app.get('/api/modes', (_req, res) => {
    res.json({ current: tradingModeService.getMode(), available: tradingModeService.getAvailableModes() });
  });

  app.post('/api/modes', (req, res, next) => {
    try {
      const { mode } = req.body;
      const updated = tradingModeService.setMode(mode);
      res.json({ mode: updated });
    } catch (error) {
      next(error);
    }
  });

  app.get('/api/assets', (_req, res) => {
    if (!tradingModeService.isPaperMode()) {
      res.status(409).json({ error: 'Endpoint available only in paper trading mode' });
      return;
    }
    res.json({ assets: marketDataService.assets });
  });

  app.get('/api/analytics', (_req, res) => {
    if (!tradingModeService.isPaperMode()) {
      res.status(409).json({ error: 'Endpoint available only in paper trading mode' });
      return;
    }
    res.json(marketDataService.getAnalytics());
  });

  app.get('/api/portfolio', (_req, res) => {
    if (!tradingModeService.isPaperMode()) {
      res.status(409).json({ error: 'Endpoint available only in paper trading mode' });
      return;
    }
    res.json(marketDataService.getPortfolio());
  });

  app.get('/api/orders', (_req, res) => {
    if (!tradingModeService.isPaperMode()) {
      res.status(409).json({ error: 'Endpoint available only in paper trading mode' });
      return;
    }
    res.json({ trades: marketDataService.getOrders() });
  });

  app.get('/api/history/:symbol', (req, res) => {
    if (!tradingModeService.isPaperMode()) {
      res.status(409).json({ error: 'Endpoint available only in paper trading mode' });
      return;
    }
    res.json({ symbol: req.params.symbol, candles: marketDataService.getHistory(req.params.symbol) });
  });

  app.get('/api/strategy/log', (_req, res) => {
    if (!tradingModeService.isPaperMode()) {
      res.status(409).json({ error: 'Endpoint available only in paper trading mode' });
      return;
    }
    res.json({ log: marketDataService.getStrategyLog() });
  });

  app.post('/api/orders', (req, res, next) => {
    try {
      if (!tradingModeService.isPaperMode()) {
        res.status(409).json({ error: 'Order endpoint available only in paper trading mode' });
        return;
      }
      const { symbol, quantity, price } = req.body;
      if (!symbol || !Number.isFinite(Number(quantity))) {
        res.status(400).json({ error: 'symbol and quantity are required' });
        return;
      }
      const numericQuantity = Number(quantity);
      const numericPrice = price ? Number(price) : undefined;
      const trade = marketDataService.placeOrder({
        symbol,
        quantity: numericQuantity,
        price: numericPrice,
        reason: 'manual-override',
        strategy: 'manual'
      });
      res.status(201).json(trade);
    } catch (error) {
      next(error);
    }
  });

  app.get('/api/live/state', (_req, res) => {
    res.json({
      mode: tradingModeService.getMode(),
      state: liveTradingService.getState()
    });
  });

  app.post('/api/live/trades', async (req, res, next) => {
    try {
      if (!tradingModeService.isLiveMode()) {
        res.status(409).json({ error: 'Live trading mode must be active to submit trades' });
        return;
      }
      const trade = await liveTradingService.submitWorkerTrade(req.body || {});
      res.status(201).json(trade);
    } catch (error) {
      next(error);
    }
  });

  app.post('/api/live/research', (req, res, next) => {
    try {
      if (!tradingModeService.isLiveMode()) {
        res.status(409).json({ error: 'Live trading mode must be active to submit research' });
        return;
      }
      const note = liveTradingService.addResearchInsight(req.body || {});
      res.status(201).json(note);
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

  return {
    app,
    marketDataService,
    liveTradingService,
    tradingModeService
  };
};

export const createServer = async ({ port = Number(process.env.PORT || 4000), marketOptions } = {}) => {
  const { app, marketDataService, liveTradingService, tradingModeService } = createApp({ marketOptions });
  const server = http.createServer(app);
  const wsService = new WebSocketService({ server, marketDataService, liveTradingService, tradingModeService });

  const start = () => new Promise((resolve) => {
    server.listen(port, () => {
      logger.info(`Crippel Trader backend listening on http://localhost:${port}`);
      resolve();
    });
  });

  const stop = () => new Promise((resolve, reject) => {
    wsService.shutdown();
    marketDataService.shutdown();
    liveTradingService.shutdown();
    server.close((error) => {
      if (error) {
        logger.error('Error while closing server', error);
        reject(error);
        return;
      }
      resolve();
    });
  });

  return {
    app,
    server,
    start,
    stop,
    marketDataService,
    liveTradingService,
    tradingModeService,
    wsService
  };
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
