import { api } from "encore.dev/api";
import { CronJob } from "encore.dev/cron";
import { db } from "../db";

function calculatePearsonCorrelation(x: number[], y: number[]): number {
  const n = x.length;
  if (n !== y.length || n === 0) return 0;

  const meanX = x.reduce((a, b) => a + b, 0) / n;
  const meanY = y.reduce((a, b) => a + b, 0) / n;

  let numerator = 0;
  let denomX = 0;
  let denomY = 0;

  for (let i = 0; i < n; i++) {
    const dx = x[i] - meanX;
    const dy = y[i] - meanY;
    numerator += dx * dy;
    denomX += dx * dx;
    denomY += dy * dy;
  }

  if (denomX === 0 || denomY === 0) return 0;
  return numerator / Math.sqrt(denomX * denomY);
}

export interface CalculateCorrelationsRequest {
  symbols: string[];
  periodDays?: number;
}

export interface CalculateCorrelationsResponse {
  calculated: number;
  errors: string[];
}

export const calculateCorrelations = api<CalculateCorrelationsRequest, CalculateCorrelationsResponse>(
  { expose: true, method: "POST", path: "/analysis/correlations/calculate" },
  async (req) => {
    const { symbols, periodDays = 30 } = req;
    let calculated = 0;
    const errors: string[] = [];

    const priceDataMap = new Map<string, number[]>();

    for (const symbol of symbols) {
      try {
        const assetId = symbol.toLowerCase();
        const rows = await db.queryAll<{ close: number }>`
          SELECT close
          FROM ohlcv_data
          WHERE asset_id = ${assetId} 
            AND interval = '1h'
            AND timestamp > NOW() - INTERVAL '${periodDays} days'
          ORDER BY timestamp ASC
        `;
        
        priceDataMap.set(assetId, rows.map(r => r.close));
      } catch (error) {
        errors.push(`Error fetching ${symbol}: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    }

    for (let i = 0; i < symbols.length; i++) {
      for (let j = i + 1; j < symbols.length; j++) {
        try {
          const asset1 = symbols[i].toLowerCase();
          const asset2 = symbols[j].toLowerCase();

          const prices1 = priceDataMap.get(asset1);
          const prices2 = priceDataMap.get(asset2);

          if (!prices1 || !prices2) continue;

          const minLength = Math.min(prices1.length, prices2.length);
          if (minLength < 20) continue;

          const p1 = prices1.slice(-minLength);
          const p2 = prices2.slice(-minLength);

          const pearson = calculatePearsonCorrelation(p1, p2);

          await db.exec`
            INSERT INTO correlations (
              asset_id_1, asset_id_2, timestamp, period_days,
              pearson_correlation
            ) VALUES (
              ${asset1}, ${asset2}, NOW(), ${periodDays}, ${pearson}
            )
            ON CONFLICT (asset_id_1, asset_id_2, timestamp, period_days)
            DO UPDATE SET pearson_correlation = EXCLUDED.pearson_correlation
          `;

          calculated++;
        } catch (error) {
          errors.push(`Error calculating correlation: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
      }
    }

    return { calculated, errors };
  }
);

export const scheduledCorrelations = api<void, CalculateCorrelationsResponse>(
  { method: "POST", path: "/analysis/correlations/calculate/scheduled" },
  async () => {
    return await calculateCorrelations({
      symbols: ["BTC", "ETH", "BNB", "SOL", "ADA", "XRP"],
      periodDays: 30
    });
  }
);

const _ = new CronJob("calculate-correlations", {
  title: "Calculate Asset Correlations",
  schedule: "0 0 * * *",
  endpoint: scheduledCorrelations
});

export interface GetCorrelationsRequest {
  symbol: string;
  periodDays?: number;
}

export interface CorrelationData {
  asset: string;
  correlation: number;
}

export interface GetCorrelationsResponse {
  symbol: string;
  periodDays: number;
  correlations: CorrelationData[];
}

export const getCorrelations = api<GetCorrelationsRequest, GetCorrelationsResponse>(
  { expose: true, method: "GET", path: "/analysis/correlations/:symbol" },
  async (req) => {
    const { symbol, periodDays = 30 } = req;
    const assetId = symbol.toLowerCase();

    const rows = await db.queryAll<{
      asset_id_1: string;
      asset_id_2: string;
      pearson_correlation: number;
    }>`
      SELECT asset_id_1, asset_id_2, pearson_correlation
      FROM correlations
      WHERE (asset_id_1 = ${assetId} OR asset_id_2 = ${assetId})
        AND period_days = ${periodDays}
      ORDER BY ABS(pearson_correlation) DESC
    `;

    const correlations = rows.map(row => ({
      asset: row.asset_id_1 === assetId ? row.asset_id_2.toUpperCase() : row.asset_id_1.toUpperCase(),
      correlation: row.pearson_correlation
    }));

    return {
      symbol: symbol.toUpperCase(),
      periodDays,
      correlations
    };
  }
);
