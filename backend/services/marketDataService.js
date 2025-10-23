const EventEmitter = require('events');
const dayjs = require('dayjs');
const seedAssets = require('../data/seedAssets');
const PortfolioService = require('./portfolioService');
const StrategyEngine = require('./strategyEngine');
const {
  calculateSMA,
  calculateEMA,
  calculateRSI,
  calculateBollingerBands,
  calculateVolatility,
  calculateDrawdown
} = require('../utils/indicators');

class MarketDataService extends EventEmitter {
  constructor() {
    super();
    this.portfolio = new PortfolioService();
    this.strategyEngine = new StrategyEngine(this.portfolio);
    this.assets = seedAssets.map((asset) => ({
      ...asset,
      price: asset.basePrice,
      lastUpdate: dayjs().toISOString(),
      change: 0,
      changePercent: 0
    }));
    this.history = new Map();
    this.snapshots = {};

    this.assets.forEach((asset) => {
      this.history.set(asset.symbol, this.generateSeedHistory(asset));
    });

    this.updateSnapshots();

    this.interval = setInterval(() => {
      this.tick();
    }, 2500);
  }

  generateSeedHistory(asset) {
    const candles = [];
    let price = asset.basePrice;
    for (let i = 0; i < 240; i += 1) {
      const variance = price * 0.012;
      const drift = price * 0.0008 * Math.sin(i / 12);
      const shock = (Math.random() - 0.5) * variance;
      const open = price;
      const close = Math.max(0.1, open + drift + shock);
      const high = Math.max(open, close) + Math.random() * variance * 0.5;
      const low = Math.min(open, close) - Math.random() * variance * 0.5;
      const volume = Math.abs((variance + shock) * 40);
      candles.push({
        timestamp: dayjs().subtract(4, 'hour').add(i, 'minute').toISOString(),
        open,
        high,
        low,
        close,
        volume
      });
      price = close;
    }
    return candles;
  }

  updateSnapshots() {
    this.snapshots = Object.fromEntries(this.assets.map((asset) => [asset.symbol, asset]));
  }

  tick() {
    this.assets = this.assets.map((asset) => {
      const history = this.history.get(asset.symbol) || [];
      const prev = history[history.length - 1] ?? { close: asset.basePrice };
      const drift = prev.close * 0.001 * Math.sin(Date.now() / 60000);
      const volatility = prev.close * (0.0025 + Math.random() * 0.0025);
      const shock = (Math.random() - 0.5) * volatility;
      const open = prev.close;
      const close = Math.max(0.1, open + drift + shock);
      const high = Math.max(open, close) + Math.random() * volatility;
      const low = Math.min(open, close) - Math.random() * volatility;
      const volume = Math.abs((shock + volatility) * 25);
      const candle = {
        timestamp: dayjs().toISOString(),
        open,
        high,
        low,
        close,
        volume
      };
      history.push(candle);
      if (history.length > 600) {
        history.shift();
      }
      this.history.set(asset.symbol, history);
      const change = close - asset.price;
      const changePercent = (change / asset.price) * 100;
      const updated = {
        ...asset,
        price: close,
        lastUpdate: candle.timestamp,
        change,
        changePercent,
        volume: candle.volume
      };
      this.runStrategy(updated.symbol, history);
      return updated;
    });

    this.updateSnapshots();
    this.broadcast();
  }

  runStrategy(symbol, history) {
    const decision = this.strategyEngine.evaluate(symbol, history);
    if (!decision) return;

    try {
      const assetMeta = this.assets.find((item) => item.symbol === symbol);
      const trade = this.portfolio.applyTrade({
        ...decision,
        sector: assetMeta?.sector ?? null
      });
      this.emit('trade', trade);
    } catch (error) {
      this.emit('error', {
        type: 'strategy-execution',
        symbol,
        message: error.message
      });
    }
  }

  getPortfolio() {
    return this.portfolio.getState(this.snapshots);
  }

  getOrders() {
    return this.portfolio.getState(this.snapshots).trades;
  }

  getStrategyLog() {
    return this.strategyEngine.getLog();
  }

  getHistory(symbol) {
    return this.history.get(symbol) || [];
  }

  getAnalytics() {
    const analytics = this.assets.map((asset) => {
      const history = this.history.get(asset.symbol) || [];
      const closes = history.map((candle) => candle.close);
      return {
        symbol: asset.symbol,
        name: asset.name,
        sector: asset.sector,
        price: asset.price,
        changePercent: asset.changePercent,
        sma21: calculateSMA(closes, 21),
        sma50: calculateSMA(closes, 50),
        ema21: calculateEMA(closes, 21),
        rsi: calculateRSI(closes, 14),
        bollinger: calculateBollingerBands(closes, 20, 2),
        volatility: calculateVolatility(closes, 30),
        drawdown: calculateDrawdown(closes.slice(-120))
      };
    });

    const leaders = [...analytics]
      .sort((a, b) => b.changePercent - a.changePercent)
      .slice(0, 3);
    const laggards = [...analytics]
      .sort((a, b) => a.changePercent - b.changePercent)
      .slice(0, 3);

    const riskBuckets = analytics.reduce((acc, asset) => {
      const vol = asset.volatility ?? 0;
      if (vol > 50) acc.high.push(asset);
      else if (vol > 25) acc.medium.push(asset);
      else acc.low.push(asset);
      return acc;
    }, { high: [], medium: [], low: [] });

    return {
      assets: analytics,
      leaders,
      laggards,
      riskBuckets,
      timestamp: dayjs().toISOString()
    };
  }

  placeOrder(order) {
    const asset = this.assets.find((item) => item.symbol === order.symbol);
    if (!asset) {
      throw new Error(`Unknown symbol ${order.symbol}`);
    }
    const decision = {
      ...order,
      price: order.price ?? asset.price,
      sector: asset.sector
    };
    const trade = this.portfolio.applyTrade(decision);
    this.emit('trade', trade);
    this.broadcast();
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
  }
}

module.exports = MarketDataService;
