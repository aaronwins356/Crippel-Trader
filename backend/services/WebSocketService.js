import { WebSocketServer } from 'ws';
import { logger } from '../utils/logger.js';

export default class WebSocketService {
  constructor({ server, marketDataService, path = '/ws/stream' }) {
    this.wss = new WebSocketServer({ server, path });
    this.marketDataService = marketDataService;
    this.clients = new Set();

    this.broadcastUpdate = this.broadcastUpdate.bind(this);
    this.broadcastTrade = this.broadcastTrade.bind(this);

    this.wss.on('connection', (socket) => {
      logger.info('WebSocket client connected');
      this.clients.add(socket);
      socket.send(JSON.stringify({
        type: 'market:update',
        market: this.marketDataService.assets,
        analytics: this.marketDataService.getAnalytics(),
        portfolio: this.marketDataService.getPortfolio(),
        strategy: { log: this.marketDataService.strategyService.getLog() }
      }));

      socket.on('close', () => {
        this.clients.delete(socket);
        logger.info('WebSocket client disconnected');
      });

      socket.on('error', (error) => {
        logger.warn('WebSocket client error', error);
      });
    });

    this.marketDataService.on('update', this.broadcastUpdate);
    this.marketDataService.on('trade', this.broadcastTrade);
  }

  broadcastUpdate(payload) {
    const data = JSON.stringify(payload);
    this.clients.forEach((client) => {
      if (client.readyState === 1) {
        client.send(data);
      }
    });
  }

  broadcastTrade(trade) {
    const message = JSON.stringify({ type: 'strategy:trade', trade });
    this.clients.forEach((client) => {
      if (client.readyState === 1) {
        client.send(message);
      }
    });
  }

  shutdown() {
    this.marketDataService.off('update', this.broadcastUpdate);
    this.marketDataService.off('trade', this.broadcastTrade);
    this.clients.forEach((client) => {
      try {
        client.close();
      } catch (error) {
        logger.warn('Failed to close client socket', error);
      }
    });
    this.clients.clear();
    this.wss.close(() => {
      logger.info('WebSocket server closed');
    });
  }
}
