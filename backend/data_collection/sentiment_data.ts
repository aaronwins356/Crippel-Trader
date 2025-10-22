import { api } from "encore.dev/api";
import { CronJob } from "encore.dev/cron";
import { secret } from "encore.dev/config";
import { db } from "../db";

const newsApiKey = secret("NewsApiKey");

export interface SyncSentimentDataRequest {
  symbols: string[];
}

export interface SyncSentimentDataResponse {
  synced: number;
  errors: string[];
}

function analyzeSentiment(text: string): number {
  const positiveWords = ['bullish', 'pump', 'moon', 'surge', 'rally', 'gain', 'profit', 'buy', 'rocket', 'green'];
  const negativeWords = ['bearish', 'dump', 'crash', 'drop', 'fall', 'loss', 'sell', 'fear', 'red', 'panic'];
  
  const lowerText = text.toLowerCase();
  let score = 0;
  
  positiveWords.forEach(word => {
    const regex = new RegExp(`\\b${word}\\b`, 'gi');
    const matches = lowerText.match(regex);
    if (matches) score += matches.length;
  });
  
  negativeWords.forEach(word => {
    const regex = new RegExp(`\\b${word}\\b`, 'gi');
    const matches = lowerText.match(regex);
    if (matches) score -= matches.length;
  });
  
  return Math.max(-1, Math.min(1, score / 10));
}

export const syncSentimentData = api<SyncSentimentDataRequest, SyncSentimentDataResponse>(
  { expose: true, method: "POST", path: "/data/sentiment/sync" },
  async (req) => {
    const { symbols } = req;
    let synced = 0;
    const errors: string[] = [];
    const apiKey = newsApiKey();

    if (!apiKey) {
      return { synced: 0, errors: ["News API key not configured"] };
    }

    for (const symbol of symbols) {
      try {
        const assetId = symbol.toLowerCase();
        const query = `${symbol} cryptocurrency OR crypto ${symbol}`;
        const url = `https://newsapi.org/v2/everything?q=${encodeURIComponent(query)}&sortBy=publishedAt&pageSize=20&language=en&apiKey=${apiKey}`;
        
        const response = await globalThis.fetch(url);
        
        if (!response.ok) {
          errors.push(`Failed to fetch sentiment for ${symbol}: ${response.statusText}`);
          continue;
        }

        const data = await response.json() as any;
        const articles = data.articles || [];

        let totalSentiment = 0;
        let positiveCount = 0;
        let negativeCount = 0;
        let neutralCount = 0;
        const keywords = new Map<string, number>();

        for (const article of articles) {
          const text = `${article.title || ''} ${article.description || ''}`;
          const sentiment = analyzeSentiment(text);
          totalSentiment += sentiment;

          if (sentiment > 0.1) positiveCount++;
          else if (sentiment < -0.1) negativeCount++;
          else neutralCount++;

          const words = text.toLowerCase().match(/\b\w{4,}\b/g) || [];
          words.forEach(word => {
            if (!['this', 'that', 'with', 'from', 'have', 'been', 'will'].includes(word)) {
              keywords.set(word, (keywords.get(word) || 0) + 1);
            }
          });
        }

        const avgSentiment = articles.length > 0 ? totalSentiment / articles.length : 0;
        const topKeywords = Array.from(keywords.entries())
          .sort((a, b) => b[1] - a[1])
          .slice(0, 10)
          .map(([word]) => word);

        await db.exec`
          INSERT INTO sentiment_data (
            asset_id, timestamp, source, sentiment_score,
            positive_count, negative_count, neutral_count,
            volume_mentions, top_keywords
          ) VALUES (
            ${assetId}, NOW(), 'news_api', ${avgSentiment},
            ${positiveCount}, ${negativeCount}, ${neutralCount},
            ${articles.length}, ${topKeywords}
          )
        `;

        synced++;
      } catch (error) {
        errors.push(`Error syncing ${symbol}: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    }

    return { synced, errors };
  }
);

export const scheduledSentimentSync = api<void, SyncSentimentDataResponse>(
  { method: "POST", path: "/data/sentiment/sync/scheduled" },
  async () => {
    return await syncSentimentData({ symbols: ["BTC", "ETH", "BNB", "SOL"] });
  }
);

const _ = new CronJob("sentiment-data-sync", {
  title: "Sync Sentiment Data",
  schedule: "0 */2 * * *",
  endpoint: scheduledSentimentSync
});

export interface GetSentimentRequest {
  symbol: string;
  days?: number;
}

export interface SentimentPoint {
  timestamp: Date;
  source: string;
  sentimentScore: number;
  positiveCount: number;
  negativeCount: number;
  neutralCount: number;
  volumeMentions: number;
  topKeywords: string[];
}

export interface GetSentimentResponse {
  symbol: string;
  currentSentiment: number;
  trend: string;
  data: SentimentPoint[];
}

export const getSentiment = api<GetSentimentRequest, GetSentimentResponse>(
  { expose: true, method: "GET", path: "/data/sentiment/:symbol" },
  async (req) => {
    const { symbol, days = 7 } = req;
    const assetId = symbol.toLowerCase();

    const rows = await db.queryAll<{
      timestamp: Date;
      source: string;
      sentiment_score: number;
      positive_count: number;
      negative_count: number;
      neutral_count: number;
      volume_mentions: number;
      top_keywords: string[];
    }>`
      SELECT 
        timestamp, source, sentiment_score,
        positive_count, negative_count, neutral_count,
        volume_mentions, top_keywords
      FROM sentiment_data
      WHERE asset_id = ${assetId}
        AND timestamp > NOW() - INTERVAL '${days} days'
      ORDER BY timestamp DESC
    `;

    const data = rows.reverse().map(row => ({
      timestamp: row.timestamp,
      source: row.source,
      sentimentScore: row.sentiment_score,
      positiveCount: row.positive_count,
      negativeCount: row.negative_count,
      neutralCount: row.neutral_count,
      volumeMentions: row.volume_mentions,
      topKeywords: row.top_keywords
    }));

    const currentSentiment = data.length > 0 ? data[data.length - 1].sentimentScore : 0;
    const previousSentiment = data.length > 1 ? data[data.length - 2].sentimentScore : currentSentiment;
    
    let trend = "neutral";
    if (currentSentiment > previousSentiment + 0.1) trend = "improving";
    else if (currentSentiment < previousSentiment - 0.1) trend = "declining";

    return {
      symbol: symbol.toUpperCase(),
      currentSentiment,
      trend,
      data
    };
  }
);
