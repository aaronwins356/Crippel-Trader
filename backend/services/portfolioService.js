const dayjs = require('dayjs');

class PortfolioService {
  constructor(initialCapital = 250000) {
    this.initialCapital = initialCapital;
    this.cash = initialCapital;
    this.positions = new Map();
    this.trades = [];
    this.realizedPnL = 0;
  }

  getState(marketSnapshots = {}) {
    const positions = Array.from(this.positions.values()).map((position) => {
      const latestPrice = marketSnapshots[position.symbol]?.price ?? position.avgPrice;
      const marketValue = position.quantity * latestPrice;
      const unrealized = (latestPrice - position.avgPrice) * position.quantity;
      return {
        ...position,
        latestPrice,
        marketValue,
        unrealizedPnL: unrealized
      };
    });

    const grossExposure = positions.reduce((acc, pos) => acc + Math.abs(pos.marketValue), 0);
    const netExposure = positions.reduce((acc, pos) => acc + pos.marketValue, 0);

    return {
      cash: this.cash,
      positions,
      trades: this.trades.slice(-150),
      realizedPnL: this.realizedPnL,
      grossExposure,
      netExposure,
      leverage: grossExposure ? (grossExposure / this.getEquity(marketSnapshots)) : 0,
      equity: this.getEquity(marketSnapshots)
    };
  }

  getEquity(marketSnapshots = {}) {
    const positionValue = Array.from(this.positions.values()).reduce((acc, position) => {
      const latestPrice = marketSnapshots[position.symbol]?.price ?? position.avgPrice;
      return acc + position.quantity * latestPrice;
    }, 0);
    return this.cash + positionValue + this.realizedPnL;
  }

  applyTrade({ symbol, quantity, price, reason = 'manual', strategy = 'discretionary', sector = null }) {
    if (!quantity || !price) {
      throw new Error('Invalid trade payload');
    }

    const cost = quantity * price;
    if (quantity > 0 && this.cash < cost) {
      throw new Error('Insufficient cash to execute trade');
    }

    const position = this.positions.get(symbol) || {
      symbol,
      quantity: 0,
      avgPrice: price,
      sector
    };

    const positionSign = Math.sign(position.quantity);
    const tradeSign = Math.sign(quantity);
    const isReducing = position.quantity !== 0 && tradeSign !== 0 && tradeSign !== positionSign;

    if (isReducing) {
      const closingQuantity = Math.min(Math.abs(quantity), Math.abs(position.quantity));
      const pnl = (price - position.avgPrice) * closingQuantity * positionSign;
      this.realizedPnL += pnl;
    }

    const newQuantity = position.quantity + quantity;

    if (newQuantity === 0) {
      this.positions.delete(symbol);
    } else if (position.quantity === 0 || (tradeSign !== 0 && tradeSign === positionSign && !isReducing)) {
      const totalCost = position.avgPrice * position.quantity + price * quantity;
      const avgPrice = totalCost / newQuantity;
      this.positions.set(symbol, {
        ...position,
        quantity: newQuantity,
        avgPrice,
        sector: position.sector || sector
      });
    } else if (isReducing && Math.sign(newQuantity) === positionSign) {
      this.positions.set(symbol, {
        ...position,
        quantity: newQuantity
      });
    } else {
      this.positions.set(symbol, {
        ...position,
        quantity: newQuantity,
        avgPrice: price,
        sector: position.sector || sector
      });
    }

    this.cash -= cost;

    const trade = {
      id: `${symbol}-${Date.now()}`,
      timestamp: dayjs().toISOString(),
      symbol,
      quantity,
      price,
      cost,
      reason,
      strategy,
      sector: position.sector || sector
    };
    this.trades.push(trade);
    return trade;
  }
}

module.exports = PortfolioService;
