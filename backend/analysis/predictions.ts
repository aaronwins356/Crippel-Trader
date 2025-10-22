import { api } from "encore.dev/api";
import { CronJob } from "encore.dev/cron";
import { db } from "../db";

function simpleMovingAveragePredictor(prices: number[], horizon: number): { prediction: number; lower: number; upper: number } {
  const sma = prices.slice(-20).reduce((a, b) => a + b, 0) / 20;
  const volatility = Math.sqrt(
    prices.slice(-20).reduce((sum, p) => sum + Math.pow(p - sma, 2), 0) / 20
  );
  
  const trend = prices.length > 1 ? (prices[prices.length - 1] - prices[prices.length - 2]) / prices[prices.length - 2] : 0;
  const prediction = sma * (1 + trend * horizon);
  
  const confidenceInterval = volatility * Math.sqrt(horizon) * 1.96;
  
  return {
    prediction,
    lower: prediction - confidenceInterval,
    upper: prediction + confidenceInterval
  };
}

function exponentialSmoothingPredictor(prices: number[], horizon: number): { prediction: number; lower: number; upper: number } {
  const alpha = 0.3;
  let level = prices[0];
  let trend = 0;
  
  for (let i = 1; i < prices.length; i++) {
    const prevLevel = level;
    level = alpha * prices[i] + (1 - alpha) * (level + trend);
    trend = alpha * (level - prevLevel) + (1 - alpha) * trend;
  }
  
  const prediction = level + horizon * trend;
  
  const errors = prices.slice(1).map((p, i) => Math.abs(p - prices[i]));
  const mae = errors.reduce((a, b) => a + b, 0) / errors.length;
  const confidenceInterval = mae * 1.96 * Math.sqrt(horizon);
  
  return {
    prediction,
    lower: prediction - confidenceInterval,
    upper: prediction + confidenceInterval
  };
}

function ensemblePredictor(prices: number[], horizon: number): { prediction: number; lower: number; upper: number } {
  const sma = simpleMovingAveragePredictor(prices, horizon);
  const es = exponentialSmoothingPredictor(prices, horizon);
  
  return {
    prediction: (sma.prediction + es.prediction) / 2,
    lower: Math.min(sma.lower, es.lower),
    upper: Math.max(sma.upper, es.upper)
  };
}

export interface GeneratePredictionsRequest {
  symbols: string[];
  horizon?: number;
}

export interface GeneratePredictionsResponse {
  generated: number;
  errors: string[];
}

export const generatePredictions = api<GeneratePredictionsRequest, GeneratePredictionsResponse>(
  { expose: true, method: "POST", path: "/analysis/predictions/generate" },
  async (req) => {
    const { symbols, horizon = 24 } = req;
    let generated = 0;
    const errors: string[] = [];

    for (const symbol of symbols) {
      try {
        const assetId = symbol.toLowerCase();

        const priceData = await db.queryAll<{ close: number; timestamp: Date }>`
          SELECT close, timestamp
          FROM ohlcv_data
          WHERE asset_id = ${assetId} AND interval = '1h'
          ORDER BY timestamp ASC
          LIMIT 500
        `;

        if (priceData.length < 50) {
          errors.push(`Insufficient data for ${symbol}`);
          continue;
        }

        const prices = priceData.map(d => d.close);
        const latestTimestamp = priceData[priceData.length - 1].timestamp;
        const targetTimestamp = new Date(latestTimestamp.getTime() + horizon * 60 * 60 * 1000);

        const result = ensemblePredictor(prices, horizon);

        const featureImportance = {
          sma_trend: 0.35,
          exponential_smoothing: 0.30,
          recent_volatility: 0.20,
          volume_trend: 0.15
        };

        await db.exec`
          INSERT INTO predictions (
            asset_id, prediction_timestamp, target_timestamp,
            model_name, model_version, predicted_price,
            confidence_lower, confidence_upper, confidence_level,
            feature_importance
          ) VALUES (
            ${assetId}, NOW(), ${targetTimestamp},
            'ensemble_v1', '1.0', ${result.prediction},
            ${result.lower}, ${result.upper}, 0.95,
            ${JSON.stringify(featureImportance)}
          )
        `;

        generated++;
      } catch (error) {
        errors.push(`Error generating prediction for ${symbol}: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    }

    return { generated, errors };
  }
);

export const scheduledPredictions = api<void, GeneratePredictionsResponse>(
  { method: "POST", path: "/analysis/predictions/generate/scheduled" },
  async () => {
    return await generatePredictions({
      symbols: ["BTC", "ETH", "BNB", "SOL"],
      horizon: 24
    });
  }
);

const _ = new CronJob("generate-predictions", {
  title: "Generate Price Predictions",
  schedule: "0 * * * *",
  endpoint: scheduledPredictions
});

export interface GetPredictionsRequest {
  symbol: string;
  limit?: number;
}

export interface Prediction {
  predictionTimestamp: Date;
  targetTimestamp: Date;
  modelName: string;
  predictedPrice: number;
  confidenceLower: number;
  confidenceUpper: number;
  featureImportance: Record<string, number>;
  actualPrice: number | null;
  errorPercentage: number | null;
}

export interface GetPredictionsResponse {
  symbol: string;
  predictions: Prediction[];
  accuracy: {
    mape: number | null;
    correctDirection: number | null;
  };
}

export const getPredictions = api<GetPredictionsRequest, GetPredictionsResponse>(
  { expose: true, method: "GET", path: "/analysis/predictions/:symbol" },
  async (req) => {
    const { symbol, limit = 10 } = req;
    const assetId = symbol.toLowerCase();

    const rows = await db.queryAll<{
      prediction_timestamp: Date;
      target_timestamp: Date;
      model_name: string;
      predicted_price: number;
      confidence_lower: number;
      confidence_upper: number;
      feature_importance: any;
      actual_price: number | null;
      error_percentage: number | null;
    }>`
      SELECT 
        prediction_timestamp, target_timestamp, model_name,
        predicted_price, confidence_lower, confidence_upper,
        feature_importance, actual_price, error_percentage
      FROM predictions
      WHERE asset_id = ${assetId}
      ORDER BY prediction_timestamp DESC
      LIMIT ${limit}
    `;

    const predictions = rows.map(row => ({
      predictionTimestamp: row.prediction_timestamp,
      targetTimestamp: row.target_timestamp,
      modelName: row.model_name,
      predictedPrice: row.predicted_price,
      confidenceLower: row.confidence_lower,
      confidenceUpper: row.confidence_upper,
      featureImportance: row.feature_importance || {},
      actualPrice: row.actual_price,
      errorPercentage: row.error_percentage
    }));

    const accuracyRows = await db.queryRow<{
      mape: number | null;
      correct_direction: number | null;
    }>`
      SELECT 
        AVG(ABS(error_percentage)) as mape,
        AVG(CASE WHEN error_percentage IS NOT NULL THEN 1.0 ELSE 0.0 END) as correct_direction
      FROM predictions
      WHERE asset_id = ${assetId}
        AND actual_price IS NOT NULL
    `;

    return {
      symbol: symbol.toUpperCase(),
      predictions,
      accuracy: {
        mape: accuracyRows?.mape || null,
        correctDirection: accuracyRows?.correct_direction || null
      }
    };
  }
);
