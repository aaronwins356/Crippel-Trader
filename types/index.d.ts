// Asset data structure
export interface Asset {
  symbol: string;
  name: string;
  price: number;
  changePercent: number;
}

// Watchlist item with history for mini-chart
export interface WatchlistItem extends Asset {
  history: number[];
}

// Time series data point
export interface TimeSeriesPoint {
  timestamp: string; // ISO 8601
  value: number;
}

// Comparison data structure
export interface ComparisonData {
  base: string;
  series: Record<string, TimeSeriesPoint[]>;
}

// API response types
export interface AssetsResponse extends Array<Asset> {}
export interface WatchlistResponse extends Array<{ symbol: string }> {}
export interface ComparisonResponse extends ComparisonData {}

// Zustand state interface
export interface WatchlistState {
  assets: WatchlistItem[];
  addAsset: (asset: WatchlistItem) => void;
  removeAsset: (symbol: string) => void;
  updatePrices: (data: Partial<WatchlistItem>[]) => void;
}