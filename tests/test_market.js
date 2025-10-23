import MarketDataService from '../backend/services/MarketDataService.js';

describe('MarketDataService', () => {
  let service;

  beforeAll(() => {
    service = new MarketDataService({ intervalMs: 3600000 });
    service.tick();
  });

  afterAll(() => {
    service.shutdown();
  });

  test('produces analytics with indicators', () => {
    const analytics = service.getAnalytics();
    expect(analytics.assets.length).toBeGreaterThan(0);
    const asset = analytics.assets[0];
    expect(asset).toHaveProperty('rsi');
    expect(asset).toHaveProperty('macd');
    expect(asset).toHaveProperty('bollinger');
    expect(asset.rsi).toBeGreaterThanOrEqual(0);
    expect(asset.macd).toHaveProperty('macd');
  });

  test('maintains rolling history for assets', () => {
    const [first] = service.assets;
    const history = service.getHistory(first.symbol);
    expect(history.length).toBeGreaterThan(0);
    expect(history[0]).toHaveProperty('open');
    expect(history[0]).toHaveProperty('close');
  });
});
