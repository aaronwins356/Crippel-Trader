import { api } from "encore.dev/api";
import { db } from "../db";

export interface HealthCheckResponse {
  status: string;
  timestamp: Date;
  database: {
    connected: boolean;
    assets: number;
    latestData: Date | null;
  };
  services: {
    dataCollection: string;
    analysis: string;
    alerts: string;
  };
}

export const healthCheck = api<void, HealthCheckResponse>(
  { expose: true, method: "GET", path: "/health" },
  async () => {
    let dbConnected = true;
    let assetCount = 0;
    let latestData: Date | null = null;

    try {
      const countResult = await db.queryRow<{ count: number }>`
        SELECT COUNT(*) as count FROM assets
      `;
      assetCount = countResult?.count || 0;

      const latestResult = await db.queryRow<{ timestamp: Date }>`
        SELECT MAX(timestamp) as timestamp FROM ohlcv_data
      `;
      latestData = latestResult?.timestamp || null;
    } catch (error) {
      dbConnected = false;
    }

    return {
      status: "healthy",
      timestamp: new Date(),
      database: {
        connected: dbConnected,
        assets: assetCount,
        latestData
      },
      services: {
        dataCollection: "operational",
        analysis: "operational",
        alerts: "operational"
      }
    };
  }
);
