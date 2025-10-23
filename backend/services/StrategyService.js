import { calculateEMA, calculateMACD, calculateRSI } from '../utils/indicators.js';
import { logger } from '../utils/logger.js';

export default class StrategyService {
  constructor(portfolioService) {
    this.portfolioService = portfolioService;
    this.log = [];
    this.lastSignals = new Map();
  }

  record(event) {
    this.log.push(event);
    if (this.log.length > 300) {
      this.log.shift();
    }
    logger.debug('Strategy event', event);
  }

  getLog() {
    return [...this.log].reverse();
  }

  getPosition(symbol) {
    return this.portfolioService.positions.get(symbol) || { quantity: 0, avgPrice: 0 };
  }

  process(symbol, candles, meta) {
    if (!candles?.length) return null;

    const closes = candles.map((candle) => candle.close);
    if (closes.length < 35) return null;

    const price = closes[closes.length - 1];
    const rsi = calculateRSI(closes, 14);
    const emaFast = calculateEMA(closes, 21);
    const emaSlow = calculateEMA(closes, 55);
    const macd = calculateMACD(closes, 12, 26, 9);

    if (!rsi || !emaFast || !emaSlow || !macd) return null;

    const histogramSlope = macd.histogram - (this.lastSignals.get(symbol)?.histogram ?? macd.histogram);
    const signal = {
      symbol,
      timestamp: candles[candles.length - 1].timestamp,
      price,
      rsi,
      emaFast,
      emaSlow,
      macd: macd.macd,
      macdSignal: macd.signal,
      histogram: macd.histogram,
      histogramSlope
    };

    const position = this.getPosition(symbol);
    const baseRisk = Math.max(1, Math.round((this.portfolioService.initialCapital * 0.02) / price));
    let action = null;
    let quantity = 0;

    if (macd.histogram > 0 && histogramSlope >= 0 && rsi <= 70 && price > emaFast) {
      if (position.quantity <= 0) {
        action = 'BUY';
        quantity = position.quantity < 0 ? Math.abs(position.quantity) + baseRisk : baseRisk;
      }
    } else if (macd.histogram <= 0.1 && histogramSlope <= 0 && rsi >= 40 && price < emaFast) {
      if (position.quantity > 0) {
        action = 'SELL';
        quantity = -Math.min(position.quantity, baseRisk);
      }
    } else if (rsi < 28 && position.quantity <= 0) {
      action = 'BUY';
      quantity = baseRisk;
    } else if (rsi > 72 && position.quantity > 0) {
      action = 'SELL';
      quantity = -Math.min(position.quantity, baseRisk);
    }

    this.lastSignals.set(symbol, { histogram: macd.histogram, timestamp: signal.timestamp });

    if (!action || quantity === 0) return null;

    const trade = this.portfolioService.applyTrade({
      symbol,
      quantity,
      price,
      reason: action === 'BUY' ? 'signal-long' : 'signal-exit',
      strategy: 'MACD-RSI',
      sector: meta?.sector ?? null
    });

    const event = {
      ...signal,
      action,
      quantity,
      tradeId: trade.id
    };
    this.record(event);
    return trade;
  }
}
