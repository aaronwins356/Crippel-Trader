const dayjs = require('dayjs');
const {
  calculateSMA,
  calculateEMA,
  calculateRSI,
  calculateBollingerBands
} = require('../utils/indicators');

class StrategyEngine {
  constructor(portfolioService) {
    this.portfolio = portfolioService;
    this.log = [];
  }

  getLog() {
    return this.log.slice(-200);
  }

  evaluate(symbol, history) {
    const closes = history.map((candle) => candle.close);
    if (closes.length < 50) {
      return null;
    }

    const fast = calculateSMA(closes, 8);
    const slow = calculateSMA(closes, 34);
    const ema = calculateEMA(closes, 21);
    const rsi = calculateRSI(closes, 14);
    const bands = calculateBollingerBands(closes, 20, 2);
    const lastClose = closes[closes.length - 1];

    const existing = this.portfolio.positions.get(symbol);
    let action = null;
    let size = 0;

    if (fast && slow && fast > slow && rsi && rsi < 65) {
      action = 'BUY';
      size = Math.max(1, Math.round(1000 / lastClose));
    } else if (fast && slow && fast < slow && existing && existing.quantity > 0) {
      action = 'SELL';
      size = existing.quantity;
    } else if (bands && existing && existing.quantity > 0 && lastClose < bands.lower) {
      action = 'ADD';
      size = Math.max(1, Math.round(existing.quantity * 0.3));
    } else if (bands && existing && existing.quantity > 0 && lastClose > bands.upper * 1.02) {
      action = 'TRIM';
      size = Math.max(1, Math.round(existing.quantity * 0.5));
    }

    if (!action || size === 0) {
      return null;
    }

    const quantity = action === 'SELL' || action === 'TRIM' ? -size : size;

    const entry = {
      id: `${symbol}-${Date.now()}`,
      timestamp: dayjs().toISOString(),
      symbol,
      action,
      size,
      price: lastClose,
      rsi,
      fast,
      slow,
      ema
    };
    this.log.push(entry);

    return {
      symbol,
      quantity,
      price: lastClose,
      reason: `strategy-${action.toLowerCase()}`,
      strategy: 'quantitative-core'
    };
  }
}

module.exports = StrategyEngine;
