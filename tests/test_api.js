import request from 'supertest';
import { createApp } from '../backend/server.js';

describe('REST API', () => {
  let app;
  let marketDataService;

  beforeAll(() => {
    ({ app, marketDataService } = createApp({ marketOptions: { intervalMs: 3600000 } }));
    marketDataService.tick();
  });

  afterAll(() => {
    marketDataService.shutdown();
  });

  test('GET /api/assets returns synthetic instruments', async () => {
    const response = await request(app).get('/api/assets');
    expect(response.status).toBe(200);
    expect(Array.isArray(response.body.assets)).toBe(true);
    expect(response.body.assets.length).toBeGreaterThan(0);
  });

  test('GET /api/history/:symbol returns candle history', async () => {
    const symbol = marketDataService.assets[0].symbol;
    const response = await request(app).get(`/api/history/${symbol}`);
    expect(response.status).toBe(200);
    expect(response.body.symbol).toBe(symbol);
    expect(Array.isArray(response.body.candles)).toBe(true);
    expect(response.body.candles.length).toBeGreaterThan(0);
  });

  test('POST /api/orders places manual trade', async () => {
    const symbol = marketDataService.assets[0].symbol;
    const response = await request(app).post('/api/orders').send({ symbol, quantity: 1 });
    expect(response.status).toBe(201);
    expect(response.body.symbol).toBe(symbol);

    const portfolio = await request(app).get('/api/portfolio');
    expect(portfolio.status).toBe(200);
    const position = portfolio.body.positions.find((p) => p.symbol === symbol);
    expect(position).toBeDefined();
    expect(position.quantity).toBeGreaterThan(0);
  });
});
