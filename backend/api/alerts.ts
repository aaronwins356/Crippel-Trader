import { api } from "encore.dev/api";
import { CronJob } from "encore.dev/cron";
import { db } from "../db";

export interface CreateAlertRequest {
  assetId: string;
  alertType: string;
  severity: string;
  title: string;
  description?: string;
  metadata?: Record<string, any>;
}

export interface CreateAlertResponse {
  id: number;
}

export const createAlert = api<CreateAlertRequest, CreateAlertResponse>(
  { expose: true, method: "POST", path: "/api/alerts" },
  async (req) => {
    const { assetId, alertType, severity, title, description, metadata } = req;

    const result = await db.queryRow<{ id: number }>`
      INSERT INTO alerts (
        asset_id, alert_type, severity, title, description, metadata
      ) VALUES (
        ${assetId}, ${alertType}, ${severity}, ${title}, ${description || null}, ${JSON.stringify(metadata || {})}
      )
      RETURNING id
    `;

    if (!result) {
      throw new Error("Failed to create alert");
    }

    return { id: result.id };
  }
);

export interface GetAlertsRequest {
  acknowledged?: boolean;
  limit?: number;
}

export interface Alert {
  id: number;
  assetId: string;
  alertType: string;
  severity: string;
  title: string;
  description: string | null;
  metadata: Record<string, any>;
  triggeredAt: Date;
  acknowledged: boolean;
  acknowledgedAt: Date | null;
}

export interface GetAlertsResponse {
  alerts: Alert[];
}

export const getAlerts = api<GetAlertsRequest, GetAlertsResponse>(
  { expose: true, method: "GET", path: "/api/alerts" },
  async (req) => {
    const { acknowledged, limit = 50 } = req;

    let query;
    if (acknowledged === undefined) {
      query = db.queryAll<{
        id: number;
        asset_id: string;
        alert_type: string;
        severity: string;
        title: string;
        description: string | null;
        metadata: any;
        triggered_at: Date;
        acknowledged: boolean;
        acknowledged_at: Date | null;
      }>`
        SELECT *
        FROM alerts
        ORDER BY triggered_at DESC
        LIMIT ${limit}
      `;
    } else {
      query = db.queryAll<{
        id: number;
        asset_id: string;
        alert_type: string;
        severity: string;
        title: string;
        description: string | null;
        metadata: any;
        triggered_at: Date;
        acknowledged: boolean;
        acknowledged_at: Date | null;
      }>`
        SELECT *
        FROM alerts
        WHERE acknowledged = ${acknowledged}
        ORDER BY triggered_at DESC
        LIMIT ${limit}
      `;
    }

    const rows = await query;

    const alerts = rows.map(row => ({
      id: row.id,
      assetId: row.asset_id,
      alertType: row.alert_type,
      severity: row.severity,
      title: row.title,
      description: row.description,
      metadata: row.metadata || {},
      triggeredAt: row.triggered_at,
      acknowledged: row.acknowledged,
      acknowledgedAt: row.acknowledged_at
    }));

    return { alerts };
  }
);

export interface AcknowledgeAlertRequest {
  id: number;
}

export interface AcknowledgeAlertResponse {
  success: boolean;
}

export const acknowledgeAlert = api<AcknowledgeAlertRequest, AcknowledgeAlertResponse>(
  { expose: true, method: "POST", path: "/api/alerts/:id/acknowledge" },
  async (req) => {
    const { id } = req;

    await db.exec`
      UPDATE alerts
      SET acknowledged = TRUE, acknowledged_at = NOW()
      WHERE id = ${id}
    `;

    return { success: true };
  }
);

interface DetectAnomaliesRequest {
  symbols: string[];
}

interface DetectAnomaliesResponse {
  detected: number;
}

export const detectAnomalies = api<DetectAnomaliesRequest, DetectAnomaliesResponse>(
  { method: "POST", path: "/api/alerts/detect" },
  async (req) => {
    const { symbols } = req;
    let detected = 0;

    for (const symbol of symbols) {
      try {
        const assetId = symbol.toLowerCase();

        const indicators = await db.queryRow<{
          rsi_14: number;
          stochastic_k: number;
          macd_histogram: number;
        }>`
          SELECT rsi_14, stochastic_k, macd_histogram
          FROM technical_indicators
          WHERE asset_id = ${assetId}
          ORDER BY timestamp DESC
          LIMIT 1
        `;

        if (indicators) {
          if (indicators.rsi_14 > 80) {
            await createAlert({
              assetId,
              alertType: "overbought",
              severity: "warning",
              title: `${symbol} Extreme Overbought`,
              description: `RSI at ${indicators.rsi_14.toFixed(2)} - critically overbought`,
              metadata: { rsi: indicators.rsi_14 }
            });
            detected++;
          } else if (indicators.rsi_14 < 20) {
            await createAlert({
              assetId,
              alertType: "oversold",
              severity: "warning",
              title: `${symbol} Extreme Oversold`,
              description: `RSI at ${indicators.rsi_14.toFixed(2)} - critically oversold`,
              metadata: { rsi: indicators.rsi_14 }
            });
            detected++;
          }
        }

        const onchain = await db.queryAll<{
          exchange_inflow: number;
          whale_transactions: number;
        }>`
          SELECT exchange_inflow, whale_transactions
          FROM onchain_metrics
          WHERE asset_id = ${assetId}
          ORDER BY timestamp DESC
          LIMIT 2
        `;

        if (onchain.length === 2) {
          const inflowIncrease = ((onchain[0].exchange_inflow || 0) - (onchain[1].exchange_inflow || 0)) / (onchain[1].exchange_inflow || 1);
          if (inflowIncrease > 0.5) {
            await createAlert({
              assetId,
              alertType: "whale_movement",
              severity: "info",
              title: `${symbol} Large Exchange Inflow`,
              description: `Exchange inflow increased by ${(inflowIncrease * 100).toFixed(1)}%`,
              metadata: { inflowIncrease }
            });
            detected++;
          }
        }

        const sentiment = await db.queryRow<{
          sentiment_score: number;
        }>`
          SELECT sentiment_score
          FROM sentiment_data
          WHERE asset_id = ${assetId}
          ORDER BY timestamp DESC
          LIMIT 1
        `;

        if (sentiment && Math.abs(sentiment.sentiment_score) > 0.7) {
          await createAlert({
            assetId,
            alertType: "sentiment_spike",
            severity: "info",
            title: `${symbol} Sentiment ${sentiment.sentiment_score > 0 ? 'Surge' : 'Drop'}`,
            description: `Sentiment score at ${sentiment.sentiment_score.toFixed(2)}`,
            metadata: { sentimentScore: sentiment.sentiment_score }
          });
          detected++;
        }
      } catch (error) {
        console.error(`Error detecting anomalies for ${symbol}:`, error);
      }
    }

    return { detected };
  }
);

export const scheduledAnomalyDetection = api<void, DetectAnomaliesResponse>(
  { method: "POST", path: "/api/alerts/detect/scheduled" },
  async () => {
    return await detectAnomalies({ symbols: ["BTC", "ETH", "BNB", "SOL", "ADA", "XRP"] });
  }
);

const _ = new CronJob("detect-anomalies", {
  title: "Detect Market Anomalies",
  schedule: "*/15 * * * *",
  endpoint: scheduledAnomalyDetection
});
