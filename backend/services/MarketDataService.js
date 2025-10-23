import EventEmitter from 'events';
import dayjs from 'dayjs';
import seedAssets from '../data/seedAssets.js';
import PortfolioService from './PortfolioService.js';
import StrategyService from './StrategyService.js';
import {
  calculateBollingerBands,
  calculateDrawdown,
  calculateEMA,
  calculateMACD,
  calculateRSI,
  calculateSMA,
  calculateVolatility,
  normalizeNumber
} from '../utils/indicators.js';
import { logger } from '../utils/logger.js';

const HISTORY_LIMIT = 720;
const SNAPSHOT_LIMIT = 240;

export default class MarketDataService extends EventEmitter {
  constructor({ intervalMs = 2500 } = {}) {
    super();
    this.intervalMs = intervalMs;
    this.portfolioService = new PortfolioService();
    this.strategyService = new StrategyService(this.portfolioService);
    this.assets = seedAssets.map((asset) => ({
      ...asset,
      price: asset.basePrice,
      lastUpdate: dayjs().toISOString(),
      change: 0,
      changePercent: 0,
      volume: 0
    }));
    this.history = new Map();
    this.snapshots = new Map();

    this.assets.forEach((asset) => {
      const candles = this.generateSeedHistory(asset);
      this.history.set(asset.symbol, candles);
    });

    this.rebuildSnapshots();

    this.interval = setInterval(() => {
      this.tick();
    }, this.intervalMs);
  }

  rebuildSnapshots() {
    this.snapshots = new Map(this.assets.map((asset) => [asset.symbol, { ...asset }]));
  }

  generateSeedHistory(asset) {
    const candles = [];
    let price = asset.basePrice;
    for (let i = 0; i < SNAPSHOT_LIMIT; i += 1) {
      const timestamp = dayjs().subtract(SNAPSHOT_LIMIT - i, 'minute').toISOString();
      const drift = price * 0.0008 * Math.sin(i / 12);
      const variance = price * 0.012;
      const shock = (Math.random() - 0.5) * variance;
      const open = price;
      const close = Math.max(0.1, open + drift + shock);
      const high = Math.max(open, close) + Math.random() * variance * 0.5;
      const low = Math.min(open, close) - Math.random() * variance * 0.5;
      const volume = Math.abs((variance + shock) * 40);
      candles.push({ timestamp, open, high, low, close, volume });
      price = close;
    }
    return candles;
  }

  tick() {
    try {
      this.assets = this.assets.map((asset) => {
        const candles = this.history.get(asset.symbol) || [];
        const previous = candles[candles.length - 1] ?? {
          close: asset.basePrice,
          volume: 0,
          timestamp: dayjs().subtract(1, 'minute').toISOString()
        };

        const drift = previous.close * (0.0012 * Math.sin(Date.now() / 60000));
        const volatility = previous.close * (0.0025 + Math.random() * 0.003);
        const shock = (Math.random() - 0.5) * volatility;
        const open = previous.close;
        const close = Math.max(0.1, open + drift + shock);
        const high = Math.max(open, close) + Math.random() * volatility;
        const low = Math.min(open, close) - Math.random() * volatility;
        const volume = Math.abs(shock) * 100 + Math.random() * 250;
        const candle = {
          timestamp: dayjs().toISOString(),
          open,
          high,
          low,
          close,
          volume
        };

        candles.push(candle);
        if (candles.length > HISTORY_LIMIT) {
          candles.shift();
        }
        this.history.set(asset.symbol, candles);

        const change = close - asset.price;
        const changePercent = asset.price === 0 ? 0 : (change / asset.price) * 100;
        const updated = {
          ...asset,
          price: normalizeNumber(close, 4),
          lastUpdate: candle.timestamp,
          change: normalizeNumber(change, 4),
          changePercent: normalizeNumber(changePercent, 2),
          volume: normalizeNumber(volume, 2)
        };

        const trade = this.strategyService.process(asset.symbol, candles, asset);
        if (trade) {
          this.emit('trade', trade);
        }

        return updated;
      });

      this.rebuildSnapshots();
      this.broadcast();
    } catch (error) {
      logger.error('Market tick failed', error);
      this.emit('error', error);
    }
  }

  getPortfolio() {
    return this.portfolioService.getState(Object.fromEntries(this.snapshots));
  }

  getOrders() {
    return this.getPortfolio().trades;
  }

  getHistory(symbol) {
    return this.history.get(symbol) || [];
  }

  getAnalytics() {
    const analytics = this.assets.map((asset) => {
      const candles = this.history.get(asset.symbol) || [];
      const closes = candles.map((candle) => candle.close);
      const bollinger = calculateBollingerBands(closes, 20, 2);
      const macd = calculateMACD(closes, 12, 26, 9);
      return {
        symbol: asset.symbol,
        name: asset.name,
        sector: asset.sector,
        class: asset.class,
        price: asset.price,
        changePercent: asset.changePercent,
        sma21: calculateSMA(closes, 21),
        sma50: calculateSMA(closes, 50),
        ema21: calculateEMA(closes, 21),
        ema100: calculateEMA(closes, 100),
        rsi: calculateRSI(closes, 14),
        macd,
        bollinger,
        volatility: calculateVolatility(closes, 30),
        drawdown: calculateDrawdown(closes.slice(-180)),
        latestCandle: candles[candles.length - 1] || null
      };
    });

    const sorted = [...analytics].sort((a, b) => (b.changePercent ?? 0) - (a.changePercent ?? 0));
    const leaders = sorted.slice(0, 3);
    const laggards = sorted.slice(-3).reverse();

    const riskBuckets = analytics.reduce((acc, asset) => {
      const vol = asset.volatility ?? 0;
      if (vol >= 80) acc.veryHigh.push(asset);
      else if (vol >= 40) acc.high.push(asset);
      else if (vol >= 20) acc.medium.push(asset);
      else acc.low.push(asset);
      return acc;
    }, { veryHigh: [], high: [], medium: [], low: [] });

    return {
      assets: analytics,
      leaders,
      laggards,
      riskBuckets,
      timestamp: dayjs().toISOString()
    };
  }

  getStrategyLog() {
    return this.strategyService.getLog();
  }

  placeOrder(order) {
    const asset = this.assets.find((item) => item.symbol === order.symbol);
    if (!asset) {
      throw new Error(`Unknown symbol ${order.symbol}`);
    }
    const trade = this.portfolioService.applyTrade({
      ...order,
      price: order.price ?? asset.price,
      sector: asset.sector
    });
    this.rebuildSnapshots();
    this.broadcast();
    this.emit('trade', trade);
    return trade;
  }

  broadcast() {
    const payload = {
      type: 'market:update',
      market: this.assets,
      analytics: this.getAnalytics(),
      portfolio: this.getPortfolio(),
      strategy: {
        log: this.getStrategyLog()
      }
    };
    this.emit('update', payload);
  }

  shutdown() {
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
    this.removeAllListeners();
    logger.info('Market data service stopped');
  }
}
