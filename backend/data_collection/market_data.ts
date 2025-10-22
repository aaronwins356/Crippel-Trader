import { api } from "encore.dev/api";
import { CronJob } from "encore.dev/cron";
import { db } from "../db";

export interface SyncMarketDataRequest {
  symbols: string[];
  interval?: string;
  limit?: number;
}

export interface SyncMarketDataResponse {
  synced: number;
  errors: string[];
}

export const syncMarketData = api<SyncMarketDataRequest, SyncMarketDataResponse>(
  { expose: true, method: "POST", path: "/data/market/sync" },
  async (req) => {
    const { symbols, interval = "1h", limit = 100 } = req;
    let synced = 0;
    const errors: string[] = [];

    for (const symbol of symbols) {
      try {
        const assetId = symbol.toLowerCase();
        
        await db.exec`
          INSERT INTO assets (id, symbol, name, asset_type)
          VALUES (${assetId}, ${symbol.toUpperCase()}, ${symbol}, 'crypto')
          ON CONFLICT (symbol) DO NOTHING
        `;

        const url = `https://api.binance.com/api/v3/klines?symbol=${symbol.toUpperCase()}USDT&interval=${interval}&limit=${limit}`;
        const response = await globalThis.fetch(url);
        
        if (!response.ok) {
          errors.push(`Failed to fetch ${symbol}: ${response.statusText}`);
          continue;
        }

        const data = await response.json() as any[];

        for (const candle of data) {
          const timestamp = new Date(candle[0]);
          const open = parseFloat(candle[1]);
          const high = parseFloat(candle[2]);
          const low = parseFloat(candle[3]);
          const close = parseFloat(candle[4]);
          const volume = parseFloat(candle[5]);

          await db.exec`
            INSERT INTO ohlcv_data (
              asset_id, timestamp, open, high, low, close, volume, interval, exchange
            ) VALUES (
              ${assetId}, ${timestamp}, ${open}, ${high}, ${low}, ${close}, ${volume}, ${interval}, 'binance'
            )
            ON CONFLICT (asset_id, timestamp, interval, exchange) 
            DO UPDATE SET 
              open = EXCLUDED.open,
              high = EXCLUDED.high,
              low = EXCLUDED.low,
              close = EXCLUDED.close,
              volume = EXCLUDED.volume
          `;
        }

        synced++;
      } catch (error) {
        errors.push(`Error syncing ${symbol}: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    }

    return { synced, errors };
  }
);

export const scheduledMarketSync = api<void, SyncMarketDataResponse>(
  { method: "POST", path: "/data/market/sync/scheduled" },
  async () => {
    return await syncMarketData({
      symbols: ["BTC", "ETH", "BNB", "SOL", "ADA", "XRP", "DOT", "AVAX"],
      interval: "1h",
      limit: 24
    });
  }
);

const _ = new CronJob("market-data-sync", {
  title: "Sync Market Data",
  schedule: "*/5 * * * *",
  endpoint: scheduledMarketSync
});

export interface GetOHLCVRequest {
  symbol: string;
  interval?: string;
  limit?: number;
}

export interface OHLCVData {
  timestamp: Date;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface GetOHLCVResponse {
  symbol: string;
  interval: string;
  data: OHLCVData[];
}

export const getOHLCV = api<GetOHLCVRequest, GetOHLCVResponse>(
  { expose: true, method: "GET", path: "/data/market/ohlcv/:symbol" },
  async (req) => {
    const { symbol, interval = "1h", limit = 100 } = req;
    const assetId = symbol.toLowerCase();

    const rows = await db.queryAll<{
      timestamp: Date;
      open: number;
      high: number;
      low: number;
      close: number;
      volume: number;
    }>`
      SELECT timestamp, open, high, low, close, volume
      FROM ohlcv_data
      WHERE asset_id = ${assetId} AND interval = ${interval}
      ORDER BY timestamp DESC
      LIMIT ${limit}
    `;

    return {
      symbol: symbol.toUpperCase(),
      interval,
      data: rows.reverse()
    };
  }
);
