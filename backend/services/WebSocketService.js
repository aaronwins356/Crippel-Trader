import { WebSocketServer } from 'ws';
import { logger } from '../utils/logger.js';

export default class WebSocketService {
  constructor({ server, marketDataService, liveTradingService, tradingModeService, path = '/ws/stream' }) {
    this.wss = new WebSocketServer({ server, path });
    this.marketDataService = marketDataService;
    this.liveTradingService = liveTradingService;
    this.tradingModeService = tradingModeService;
    this.clients = new Set();

    this.broadcastUpdate = this.broadcastUpdate.bind(this);
    this.broadcastTrade = this.broadcastTrade.bind(this);
    this.broadcastLiveUpdate = this.broadcastLiveUpdate.bind(this);
    this.broadcastModeChange = this.broadcastModeChange.bind(this);

    this.wss.on('connection', (socket) => {
      logger.info('WebSocket client connected');
      this.clients.add(socket);

      const currentMode = this.tradingModeService?.getMode?.() ?? 'paper';
      socket.send(JSON.stringify({ type: 'mode:change', mode: currentMode }));

      if (currentMode === 'live' && this.liveTradingService) {
        socket.send(JSON.stringify({ type: 'live:update', state: this.liveTradingService.getState() }));
      } else if (this.marketDataService) {
        socket.send(JSON.stringify({
          type: 'market:update',
          market: this.marketDataService.assets,
          analytics: this.marketDataService.getAnalytics(),
          portfolio: this.marketDataService.getPortfolio(),
          strategy: { log: this.marketDataService.strategyService.getLog() }
        }));
      }

      socket.on('close', () => {
        this.clients.delete(socket);
        logger.info('WebSocket client disconnected');
      });

      socket.on('error', (error) => {
        logger.warn('WebSocket client error', error);
      });
    });

    if (this.marketDataService) {
      this.marketDataService.on('update', this.broadcastUpdate);
      this.marketDataService.on('trade', this.broadcastTrade);
    }
    if (this.liveTradingService) {
      this.liveTradingService.on('update', this.broadcastLiveUpdate);
    }
    if (this.tradingModeService) {
      this.tradingModeService.on('mode:change', this.broadcastModeChange);
    }
  }

  broadcastToClients(payload) {
    const data = JSON.stringify(payload);
    this.clients.forEach((client) => {
      if (client.readyState === 1) {
        client.send(data);
      }
    });
  }

  broadcastUpdate(payload) {
    this.broadcastToClients(payload);
  }

  broadcastLiveUpdate(payload) {
    this.broadcastToClients(payload);
  }

  broadcastTrade(trade) {
    this.broadcastToClients({ type: 'strategy:trade', trade });
  }

  broadcastModeChange(event) {
    this.broadcastToClients(event);
  }

  shutdown() {
    if (this.marketDataService) {
      this.marketDataService.off('update', this.broadcastUpdate);
      this.marketDataService.off('trade', this.broadcastTrade);
    }
    if (this.liveTradingService) {
      this.liveTradingService.off('update', this.broadcastLiveUpdate);
    }
    if (this.tradingModeService) {
      this.tradingModeService.off('mode:change', this.broadcastModeChange);
    }
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
