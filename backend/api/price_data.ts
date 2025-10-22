import { api } from "encore.dev/api";
import { db } from "../db";

export interface GetPriceDataRequest {
  symbol: string;
  interval?: string;
  limit?: number;
}

export interface PricePoint {
  timestamp: Date;
  price: number;
  volume: number;
  change24h: number | null;
}

export interface GetPriceDataResponse {
  symbol: string;
  currentPrice: number;
  change24h: number;
  change24hPercent: number;
  volume24h: number;
  high24h: number;
  low24h: number;
  history: PricePoint[];
}

export const getPriceData = api<GetPriceDataRequest, GetPriceDataResponse>(
  { expose: true, method: "GET", path: "/api/price/:symbol" },
  async (req) => {
    const { symbol, interval = "1h", limit = 24 } = req;
    const assetId = symbol.toLowerCase();

    const current = await db.queryRow<{
      close: number;
      volume: number;
      timestamp: Date;
    }>`
      SELECT close, volume, timestamp
      FROM ohlcv_data
      WHERE asset_id = ${assetId} AND interval = ${interval}
      ORDER BY timestamp DESC
      LIMIT 1
    `;

    if (!current) {
      throw new Error(`No data found for ${symbol}`);
    }

    const history = await db.queryAll<{
      timestamp: Date;
      close: number;
      high: number;
      low: number;
      volume: number;
    }>`
      SELECT timestamp, close, high, low, volume
      FROM ohlcv_data
      WHERE asset_id = ${assetId} 
        AND interval = ${interval}
        AND timestamp > NOW() - INTERVAL '24 hours'
      ORDER BY timestamp ASC
    `;

    const prices = history.map(h => h.close);
    const volumes = history.map(h => h.volume);
    const highs = history.map(h => h.high);
    const lows = history.map(h => h.low);

    const currentPrice = current.close;
    const price24hAgo = history.length > 0 ? history[0].close : currentPrice;
    const change24h = currentPrice - price24hAgo;
    const change24hPercent = (change24h / price24hAgo) * 100;
    const volume24h = volumes.reduce((a, b) => a + b, 0);
    const high24h = Math.max(...highs);
    const low24h = Math.min(...lows);

    const priceHistory: PricePoint[] = history.map((h, idx) => ({
      timestamp: h.timestamp,
      price: h.close,
      volume: h.volume,
      change24h: idx > 0 ? h.close - history[idx - 1].close : null
    }));

    return {
      symbol: symbol.toUpperCase(),
      currentPrice,
      change24h,
      change24hPercent,
      volume24h,
      high24h,
      low24h,
      history: priceHistory.slice(-limit)
    };
  }
);

export interface GetAssetOverviewResponse {
  assets: Array<{
    symbol: string;
    name: string;
    currentPrice: number;
    change24h: number;
    change24hPercent: number;
    volume24h: number;
  }>;
}

export const getAssetOverview = api<void, GetAssetOverviewResponse>(
  { expose: true, method: "GET", path: "/api/overview" },
  async () => {
    const assets = await db.queryAll<{
      symbol: string;
      name: string;
    }>`
      SELECT DISTINCT symbol, name
      FROM assets
      ORDER BY symbol
    `;

    const overview = await Promise.all(
      assets.map(async (asset) => {
        try {
          const assetId = asset.symbol.toLowerCase();

          const latest = await db.queryRow<{
            close: number;
            volume: number;
          }>`
            SELECT close, volume
            FROM ohlcv_data
            WHERE asset_id = ${assetId} AND interval = '1h'
            ORDER BY timestamp DESC
            LIMIT 1
          `;

          const ago24h = await db.queryRow<{
            close: number;
          }>`
            SELECT close
            FROM ohlcv_data
            WHERE asset_id = ${assetId} 
              AND interval = '1h'
              AND timestamp <= NOW() - INTERVAL '24 hours'
            ORDER BY timestamp DESC
            LIMIT 1
          `;

          const volume24h = await db.queryRow<{
            total_volume: number;
          }>`
            SELECT COALESCE(SUM(volume), 0) as total_volume
            FROM ohlcv_data
            WHERE asset_id = ${assetId}
              AND interval = '1h'
              AND timestamp > NOW() - INTERVAL '24 hours'
          `;

          if (!latest) {
            return {
              symbol: asset.symbol,
              name: asset.name,
              currentPrice: 0,
              change24h: 0,
              change24hPercent: 0,
              volume24h: 0
            };
          }

          const currentPrice = latest.close;
          const price24hAgo = ago24h?.close || currentPrice;
          const change24h = currentPrice - price24hAgo;
          const change24hPercent = (change24h / price24hAgo) * 100;

          return {
            symbol: asset.symbol,
            name: asset.name,
            currentPrice,
            change24h,
            change24hPercent,
            volume24h: volume24h?.total_volume || 0
          };
        } catch (error) {
          return {
            symbol: asset.symbol,
            name: asset.name,
            currentPrice: 0,
            change24h: 0,
            change24hPercent: 0,
            volume24h: 0
          };
        }
      })
    );

    return { assets: overview };
  }
);
