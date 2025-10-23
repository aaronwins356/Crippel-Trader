import { logger } from '../../utils/logger.js';

export default class KrakenClient {
  constructor({ apiKey = process.env.KRAKEN_API_KEY, apiSecret = process.env.KRAKEN_API_SECRET } = {}) {
    this.apiKey = apiKey;
    this.apiSecret = apiSecret;
    this.enabled = Boolean(this.apiKey && this.apiSecret);
  }

  async submitOrder(order) {
    if (!order || !order.symbol || !order.side || !order.quantity || !order.price) {
      throw new Error('Invalid order payload for Kraken execution');
    }

    if (!this.enabled) {
      const reference = `SIM-${Date.now()}`;
      logger.info('Simulated Kraken order', { reference, order });
      return { reference, status: 'simulated' };
    }

    // Placeholder for real Kraken API integration. In production this would sign the
    // request payload with the apiSecret and submit it via HTTPS. We deliberately
    // avoid making network calls here so the service can operate in offline/demo
    // environments.
    const reference = `KRAKEN-${Date.now()}`;
    logger.info('Kraken order submitted (stub implementation)', { reference, order });
    return { reference, status: 'submitted' };
  }
}
