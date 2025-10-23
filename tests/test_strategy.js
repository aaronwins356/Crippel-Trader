import PortfolioService from '../backend/services/PortfolioService.js';
import StrategyService from '../backend/services/StrategyService.js';
import { calculateEMA, calculateMACD, calculateRSI } from '../backend/utils/indicators.js';

describe('StrategyService', () => {
  const buildCandles = (prices) => prices.map((price, index) => ({
    timestamp: new Date(Date.now() - (prices.length - index) * 60000).toISOString(),
    open: price - 0.5,
    high: price + 0.5,
    low: price - 1,
    close: price,
    volume: 100 + index
  }));

  const bullishPrices = Array.from({ length: 80 }, (_, idx) => 150 + idx * 0.05 + Math.sin(idx / 3) * 3);
  const bearishPrices = Array.from({ length: 80 }, (_, idx) => 190 - idx * 0.08 + Math.sin(idx / 4) * 0.6);

  const openLong = (strategy) => strategy.process('TEST', buildCandles(bullishPrices), { sector: 'Synthetic' });

  test('opens long positions on bullish signals', () => {
    const portfolio = new PortfolioService(100000);
    const strategy = new StrategyService(portfolio);
    const metrics = {
      rsi: calculateRSI(bullishPrices, 14),
      emaFast: calculateEMA(bullishPrices, 21),
      macd: calculateMACD(bullishPrices, 12, 26, 9),
      price: bullishPrices[bullishPrices.length - 1]
    };
    expect(metrics.rsi).toBeLessThanOrEqual(70);
    expect(metrics.price).toBeGreaterThan(metrics.emaFast);
    expect(metrics.macd.histogram).toBeGreaterThan(0);
    const trade = openLong(strategy);
    expect(trade).not.toBeNull();
    expect(portfolio.positions.get('TEST').quantity).toBeGreaterThan(0);
  });

  test('exits positions on bearish reversal', () => {
    const portfolio = new PortfolioService(100000);
    const strategy = new StrategyService(portfolio);
    const openingTrade = openLong(strategy);
    expect(openingTrade.quantity).toBeGreaterThan(0);
    const preQuantity = portfolio.positions.get('TEST').quantity;
    const metrics = {
      rsi: calculateRSI(bearishPrices, 14),
      emaFast: calculateEMA(bearishPrices, 21),
      macd: calculateMACD(bearishPrices, 12, 26, 9),
      price: bearishPrices[bearishPrices.length - 1]
    };
    expect(metrics.rsi).toBeGreaterThanOrEqual(40);
    expect(metrics.price).toBeLessThan(metrics.emaFast);
    expect(metrics.macd.histogram).toBeLessThanOrEqual(0.1);
    const exitTrade = strategy.process('TEST', buildCandles(bearishPrices), { sector: 'Synthetic' });

    expect(exitTrade).not.toBeNull();
    expect(exitTrade.quantity).toBeLessThan(0);
    const position = portfolio.positions.get('TEST');
    expect(position ? position.quantity : 0).toBeLessThan(preQuantity);
  });
});
