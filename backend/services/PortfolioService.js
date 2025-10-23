import dayjs from 'dayjs';
import { logger } from '../utils/logger.js';

export default class PortfolioService {
  constructor(initialCapital = 250000) {
    this.initialCapital = initialCapital;
    this.cash = initialCapital;
    this.positions = new Map();
    this.trades = [];
    this.realizedPnL = 0;
  }

  getEquity(marketSnapshots = {}) {
    const positionValue = Array.from(this.positions.values()).reduce((acc, position) => {
      const latestPrice = marketSnapshots[position.symbol]?.price ?? position.avgPrice;
      return acc + position.quantity * latestPrice;
    }, 0);
    return this.cash + positionValue + this.realizedPnL;
  }

  getState(marketSnapshots = {}) {
    const positions = Array.from(this.positions.values()).map((position) => {
      const latestPrice = marketSnapshots[position.symbol]?.price ?? position.avgPrice;
      const marketValue = position.quantity * latestPrice;
      const unrealizedPnL = (latestPrice - position.avgPrice) * position.quantity;
      return {
        ...position,
        latestPrice,
        marketValue,
        unrealizedPnL
      };
    });

    const grossExposure = positions.reduce((acc, pos) => acc + Math.abs(pos.marketValue), 0);
    const netExposure = positions.reduce((acc, pos) => acc + pos.marketValue, 0);
    const equity = this.getEquity(marketSnapshots);

    return {
      cash: this.cash,
      positions,
      trades: this.trades.slice(-200),
      realizedPnL: this.realizedPnL,
      grossExposure,
      netExposure,
      leverage: grossExposure === 0 || equity === 0 ? 0 : grossExposure / equity,
      equity
    };
  }

  applyTrade({ symbol, quantity, price, reason = 'manual', strategy = 'discretionary', sector = null }) {
    if (!symbol || !Number.isFinite(quantity) || quantity === 0 || !Number.isFinite(price)) {
      throw new Error('Invalid trade payload');
    }

    const existing = this.positions.get(symbol) || {
      symbol,
      quantity: 0,
      avgPrice: price,
      sector
    };

    const tradeDirection = Math.sign(quantity);
    const positionDirection = Math.sign(existing.quantity);
    const notional = quantity * price;

    if (tradeDirection > 0 && this.cash < notional) {
      throw new Error('Insufficient cash to execute trade');
    }

    let newQuantity = existing.quantity + quantity;
    const closingQuantity = positionDirection !== 0 && tradeDirection !== 0 && tradeDirection !== positionDirection
      ? Math.min(Math.abs(quantity), Math.abs(existing.quantity))
      : 0;

    if (closingQuantity > 0) {
      const pnl = (price - existing.avgPrice) * closingQuantity * positionDirection;
      this.realizedPnL += pnl;
    }

    if (newQuantity === 0) {
      this.positions.delete(symbol);
    } else if (positionDirection === 0 || tradeDirection === positionDirection) {
      const totalCost = existing.avgPrice * existing.quantity + price * quantity;
      const avgPrice = totalCost / newQuantity;
      this.positions.set(symbol, {
        symbol,
        quantity: newQuantity,
        avgPrice,
        sector: existing.sector || sector
      });
    } else {
      if (Math.sign(newQuantity) === positionDirection) {
        this.positions.set(symbol, {
          ...existing,
          quantity: newQuantity
        });
      } else {
        this.positions.set(symbol, {
          symbol,
          quantity: newQuantity,
          avgPrice: price,
          sector: existing.sector || sector
        });
      }
    }

    this.cash -= notional;

    const trade = {
      id: `${symbol}-${Date.now()}`,
      timestamp: dayjs().toISOString(),
      symbol,
      quantity,
      price,
      notional,
      reason,
      strategy,
      sector: existing.sector || sector
    };

    this.trades.push(trade);
    logger.debug('Portfolio trade executed', trade);
    return trade;
  }
}
