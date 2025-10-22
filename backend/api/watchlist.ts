import { api } from "encore.dev/api";
import { db } from "../db";

export interface AddToWatchlistRequest {
  assetId: string;
  notes?: string;
  alertEnabled?: boolean;
  priceAlertThreshold?: number;
}

export interface AddToWatchlistResponse {
  id: number;
}

export const addToWatchlist = api<AddToWatchlistRequest, AddToWatchlistResponse>(
  { expose: true, method: "POST", path: "/api/watchlist" },
  async (req) => {
    const { assetId, notes, alertEnabled = true, priceAlertThreshold } = req;

    const result = await db.queryRow<{ id: number }>`
      INSERT INTO watchlist (asset_id, notes, alert_enabled, price_alert_threshold)
      VALUES (${assetId}, ${notes || null}, ${alertEnabled}, ${priceAlertThreshold || null})
      RETURNING id
    `;

    if (!result) {
      throw new Error("Failed to add to watchlist");
    }

    return { id: result.id };
  }
);

export interface RemoveFromWatchlistRequest {
  id: number;
}

export interface RemoveFromWatchlistResponse {
  success: boolean;
}

export const removeFromWatchlist = api<RemoveFromWatchlistRequest, RemoveFromWatchlistResponse>(
  { expose: true, method: "DELETE", path: "/api/watchlist/:id" },
  async (req) => {
    const { id } = req;

    await db.exec`
      DELETE FROM watchlist
      WHERE id = ${id}
    `;

    return { success: true };
  }
);

export interface WatchlistItem {
  id: number;
  assetId: string;
  symbol: string;
  name: string;
  notes: string | null;
  alertEnabled: boolean;
  priceAlertThreshold: number | null;
  currentPrice: number | null;
  change24h: number | null;
  createdAt: Date;
}

export interface GetWatchlistResponse {
  items: WatchlistItem[];
}

export const getWatchlist = api<void, GetWatchlistResponse>(
  { expose: true, method: "GET", path: "/api/watchlist" },
  async () => {
    const rows = await db.queryAll<{
      id: number;
      asset_id: string;
      notes: string | null;
      alert_enabled: boolean;
      price_alert_threshold: number | null;
      created_at: Date;
    }>`
      SELECT *
      FROM watchlist
      ORDER BY created_at DESC
    `;

    const items = await Promise.all(
      rows.map(async (row) => {
        const asset = await db.queryRow<{
          symbol: string;
          name: string;
        }>`
          SELECT symbol, name
          FROM assets
          WHERE id = ${row.asset_id}
        `;

        const price = await db.queryRow<{
          close: number;
        }>`
          SELECT close
          FROM ohlcv_data
          WHERE asset_id = ${row.asset_id}
          ORDER BY timestamp DESC
          LIMIT 1
        `;

        const price24hAgo = await db.queryRow<{
          close: number;
        }>`
          SELECT close
          FROM ohlcv_data
          WHERE asset_id = ${row.asset_id}
            AND timestamp <= NOW() - INTERVAL '24 hours'
          ORDER BY timestamp DESC
          LIMIT 1
        `;

        const currentPrice = price?.close || null;
        const oldPrice = price24hAgo?.close || currentPrice;
        const change24h = currentPrice && oldPrice ? currentPrice - oldPrice : null;

        return {
          id: row.id,
          assetId: row.asset_id,
          symbol: asset?.symbol || row.asset_id.toUpperCase(),
          name: asset?.name || row.asset_id,
          notes: row.notes,
          alertEnabled: row.alert_enabled,
          priceAlertThreshold: row.price_alert_threshold,
          currentPrice,
          change24h,
          createdAt: row.created_at
        };
      })
    );

    return { items };
  }
);
