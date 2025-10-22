import { api } from "encore.dev/api";
import { CronJob } from "encore.dev/cron";
import { db } from "../db";

interface PriceData {
  close: number;
  high: number;
  low: number;
  volume: number;
}

function calculateRSI(prices: number[], period: number = 14): number {
  if (prices.length < period + 1) return 50;

  let gains = 0;
  let losses = 0;

  for (let i = prices.length - period; i < prices.length; i++) {
    const change = prices[i] - prices[i - 1];
    if (change > 0) gains += change;
    else losses -= change;
  }

  const avgGain = gains / period;
  const avgLoss = losses / period;

  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - (100 / (1 + rs));
}

function calculateSMA(prices: number[], period: number): number {
  if (prices.length < period) return prices[prices.length - 1] || 0;
  const slice = prices.slice(-period);
  return slice.reduce((a, b) => a + b, 0) / period;
}

function calculateEMA(prices: number[], period: number): number {
  if (prices.length < period) return prices[prices.length - 1] || 0;
  
  const multiplier = 2 / (period + 1);
  let ema = calculateSMA(prices.slice(0, period), period);
  
  for (let i = period; i < prices.length; i++) {
    ema = (prices[i] - ema) * multiplier + ema;
  }
  
  return ema;
}

function calculateMACD(prices: number[]): { macd: number; signal: number; histogram: number } {
  const ema12 = calculateEMA(prices, 12);
  const ema26 = calculateEMA(prices, 26);
  const macd = ema12 - ema26;
  
  const macdValues: number[] = [];
  for (let i = 26; i < prices.length; i++) {
    const e12 = calculateEMA(prices.slice(0, i + 1), 12);
    const e26 = calculateEMA(prices.slice(0, i + 1), 26);
    macdValues.push(e12 - e26);
  }
  
  const signal = calculateEMA(macdValues, 9);
  const histogram = macd - signal;
  
  return { macd, signal, histogram };
}

function calculateBollingerBands(prices: number[], period: number = 20, stdDev: number = 2) {
  const sma = calculateSMA(prices, period);
  const slice = prices.slice(-period);
  const variance = slice.reduce((sum, price) => sum + Math.pow(price - sma, 2), 0) / period;
  const std = Math.sqrt(variance);
  
  return {
    upper: sma + (std * stdDev),
    middle: sma,
    lower: sma - (std * stdDev)
  };
}

function calculateStochastic(data: PriceData[], period: number = 14): { k: number; d: number } {
  if (data.length < period) return { k: 50, d: 50 };
  
  const slice = data.slice(-period);
  const currentClose = slice[slice.length - 1].close;
  const lowestLow = Math.min(...slice.map(d => d.low));
  const highestHigh = Math.max(...slice.map(d => d.high));
  
  const k = ((currentClose - lowestLow) / (highestHigh - lowestLow)) * 100;
  
  const kValues: number[] = [];
  for (let i = period - 1; i < data.length; i++) {
    const s = data.slice(i - period + 1, i + 1);
    const c = s[s.length - 1].close;
    const l = Math.min(...s.map(d => d.low));
    const h = Math.max(...s.map(d => d.high));
    kValues.push(((c - l) / (h - l)) * 100);
  }
  
  const d = calculateSMA(kValues, 3);
  
  return { k, d };
}

function calculateATR(data: PriceData[], period: number = 14): number {
  if (data.length < period + 1) return 0;
  
  const trValues: number[] = [];
  for (let i = 1; i < data.length; i++) {
    const high = data[i].high;
    const low = data[i].low;
    const prevClose = data[i - 1].close;
    
    const tr = Math.max(
      high - low,
      Math.abs(high - prevClose),
      Math.abs(low - prevClose)
    );
    trValues.push(tr);
  }
  
  return calculateSMA(trValues, period);
}

export interface CalculateIndicatorsRequest {
  symbols: string[];
  interval?: string;
}

export interface CalculateIndicatorsResponse {
  calculated: number;
  errors: string[];
}

export const calculateIndicators = api<CalculateIndicatorsRequest, CalculateIndicatorsResponse>(
  { expose: true, method: "POST", path: "/analysis/indicators/calculate" },
  async (req) => {
    const { symbols, interval = "1h" } = req;
    let calculated = 0;
    const errors: string[] = [];

    for (const symbol of symbols) {
      try {
        const assetId = symbol.toLowerCase();

        const ohlcvData = await db.queryAll<{
          timestamp: Date;
          close: number;
          high: number;
          low: number;
          volume: number;
        }>`
          SELECT timestamp, close, high, low, volume
          FROM ohlcv_data
          WHERE asset_id = ${assetId} AND interval = ${interval}
          ORDER BY timestamp ASC
          LIMIT 500
        `;

        if (ohlcvData.length < 200) {
          errors.push(`Insufficient data for ${symbol}`);
          continue;
        }

        const prices = ohlcvData.map(d => d.close);
        const latest = ohlcvData[ohlcvData.length - 1];
        const timestamp = latest.timestamp;

        const rsi14 = calculateRSI(prices, 14);
        const rsi7 = calculateRSI(prices, 7);
        const macdData = calculateMACD(prices);
        const sma20 = calculateSMA(prices, 20);
        const sma50 = calculateSMA(prices, 50);
        const sma200 = calculateSMA(prices, 200);
        const ema12 = calculateEMA(prices, 12);
        const ema26 = calculateEMA(prices, 26);
        const bollinger = calculateBollingerBands(prices, 20, 2);
        const stochastic = calculateStochastic(ohlcvData, 14);
        const atr = calculateATR(ohlcvData, 14);

        await db.exec`
          INSERT INTO technical_indicators (
            asset_id, timestamp, interval,
            rsi_14, rsi_7, macd, macd_signal, macd_histogram,
            sma_20, sma_50, sma_200, ema_12, ema_26,
            bollinger_upper, bollinger_middle, bollinger_lower,
            stochastic_k, stochastic_d, atr
          ) VALUES (
            ${assetId}, ${timestamp}, ${interval},
            ${rsi14}, ${rsi7}, ${macdData.macd}, ${macdData.signal}, ${macdData.histogram},
            ${sma20}, ${sma50}, ${sma200}, ${ema12}, ${ema26},
            ${bollinger.upper}, ${bollinger.middle}, ${bollinger.lower},
            ${stochastic.k}, ${stochastic.d}, ${atr}
          )
          ON CONFLICT (asset_id, timestamp, interval)
          DO UPDATE SET
            rsi_14 = EXCLUDED.rsi_14,
            rsi_7 = EXCLUDED.rsi_7,
            macd = EXCLUDED.macd,
            macd_signal = EXCLUDED.macd_signal,
            macd_histogram = EXCLUDED.macd_histogram,
            sma_20 = EXCLUDED.sma_20,
            sma_50 = EXCLUDED.sma_50,
            sma_200 = EXCLUDED.sma_200,
            ema_12 = EXCLUDED.ema_12,
            ema_26 = EXCLUDED.ema_26,
            bollinger_upper = EXCLUDED.bollinger_upper,
            bollinger_middle = EXCLUDED.bollinger_middle,
            bollinger_lower = EXCLUDED.bollinger_lower,
            stochastic_k = EXCLUDED.stochastic_k,
            stochastic_d = EXCLUDED.stochastic_d,
            atr = EXCLUDED.atr
        `;

        calculated++;
      } catch (error) {
        errors.push(`Error calculating ${symbol}: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    }

    return { calculated, errors };
  }
);

export const scheduledIndicators = api<void, CalculateIndicatorsResponse>(
  { method: "POST", path: "/analysis/indicators/calculate/scheduled" },
  async () => {
    return await calculateIndicators({
      symbols: ["BTC", "ETH", "BNB", "SOL", "ADA", "XRP", "DOT", "AVAX"],
      interval: "1h"
    });
  }
);

const _ = new CronJob("calculate-indicators", {
  title: "Calculate Technical Indicators",
  schedule: "*/10 * * * *",
  endpoint: scheduledIndicators
});

export interface GetIndicatorsRequest {
  symbol: string;
  interval?: string;
}

export interface TechnicalIndicators {
  timestamp: Date;
  rsi14: number;
  rsi7: number;
  macd: number;
  macdSignal: number;
  macdHistogram: number;
  sma20: number;
  sma50: number;
  sma200: number;
  ema12: number;
  ema26: number;
  bollingerUpper: number;
  bollingerMiddle: number;
  bollingerLower: number;
  stochasticK: number;
  stochasticD: number;
  atr: number;
}

export interface GetIndicatorsResponse {
  symbol: string;
  interval: string;
  current: TechnicalIndicators | null;
  signals: {
    rsi: string;
    macd: string;
    stochastic: string;
    trend: string;
  };
}

export const getIndicators = api<GetIndicatorsRequest, GetIndicatorsResponse>(
  { expose: true, method: "GET", path: "/analysis/indicators/:symbol" },
  async (req) => {
    const { symbol, interval = "1h" } = req;
    const assetId = symbol.toLowerCase();

    const row = await db.queryRow<{
      timestamp: Date;
      rsi_14: number;
      rsi_7: number;
      macd: number;
      macd_signal: number;
      macd_histogram: number;
      sma_20: number;
      sma_50: number;
      sma_200: number;
      ema_12: number;
      ema_26: number;
      bollinger_upper: number;
      bollinger_middle: number;
      bollinger_lower: number;
      stochastic_k: number;
      stochastic_d: number;
      atr: number;
    }>`
      SELECT *
      FROM technical_indicators
      WHERE asset_id = ${assetId} AND interval = ${interval}
      ORDER BY timestamp DESC
      LIMIT 1
    `;

    let current = null;
    const signals = {
      rsi: "neutral",
      macd: "neutral",
      stochastic: "neutral",
      trend: "neutral"
    };

    if (row) {
      current = {
        timestamp: row.timestamp,
        rsi14: row.rsi_14,
        rsi7: row.rsi_7,
        macd: row.macd,
        macdSignal: row.macd_signal,
        macdHistogram: row.macd_histogram,
        sma20: row.sma_20,
        sma50: row.sma_50,
        sma200: row.sma_200,
        ema12: row.ema_12,
        ema26: row.ema_26,
        bollingerUpper: row.bollinger_upper,
        bollingerMiddle: row.bollinger_middle,
        bollingerLower: row.bollinger_lower,
        stochasticK: row.stochastic_k,
        stochasticD: row.stochastic_d,
        atr: row.atr
      };

      if (row.rsi_14 > 70) signals.rsi = "overbought";
      else if (row.rsi_14 < 30) signals.rsi = "oversold";

      if (row.macd > row.macd_signal) signals.macd = "bullish";
      else if (row.macd < row.macd_signal) signals.macd = "bearish";

      if (row.stochastic_k > 80) signals.stochastic = "overbought";
      else if (row.stochastic_k < 20) signals.stochastic = "oversold";

      if (row.sma_20 > row.sma_50 && row.sma_50 > row.sma_200) signals.trend = "bullish";
      else if (row.sma_20 < row.sma_50 && row.sma_50 < row.sma_200) signals.trend = "bearish";
    }

    return {
      symbol: symbol.toUpperCase(),
      interval,
      current,
      signals
    };
  }
);
