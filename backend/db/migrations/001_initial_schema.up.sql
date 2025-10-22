CREATE TABLE IF NOT EXISTS assets (
  id TEXT PRIMARY KEY,
  symbol TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  asset_type TEXT NOT NULL DEFAULT 'crypto',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_assets_symbol ON assets(symbol);

CREATE TABLE IF NOT EXISTS ohlcv_data (
  id SERIAL PRIMARY KEY,
  asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  timestamp TIMESTAMPTZ NOT NULL,
  open DECIMAL(20, 8) NOT NULL,
  high DECIMAL(20, 8) NOT NULL,
  low DECIMAL(20, 8) NOT NULL,
  close DECIMAL(20, 8) NOT NULL,
  volume DECIMAL(30, 8) NOT NULL,
  interval TEXT NOT NULL DEFAULT '1h',
  exchange TEXT NOT NULL DEFAULT 'binance',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(asset_id, timestamp, interval, exchange)
);

CREATE INDEX idx_ohlcv_asset_time ON ohlcv_data(asset_id, timestamp DESC);
CREATE INDEX idx_ohlcv_timestamp ON ohlcv_data(timestamp DESC);

CREATE TABLE IF NOT EXISTS onchain_metrics (
  id SERIAL PRIMARY KEY,
  asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  timestamp TIMESTAMPTZ NOT NULL,
  active_addresses BIGINT,
  transaction_count BIGINT,
  transaction_volume DECIMAL(30, 8),
  hash_rate DECIMAL(30, 8),
  difficulty DECIMAL(30, 8),
  exchange_inflow DECIMAL(30, 8),
  exchange_outflow DECIMAL(30, 8),
  whale_transactions BIGINT,
  supply_on_exchanges DECIMAL(30, 8),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(asset_id, timestamp)
);

CREATE INDEX idx_onchain_asset_time ON onchain_metrics(asset_id, timestamp DESC);

CREATE TABLE IF NOT EXISTS sentiment_data (
  id SERIAL PRIMARY KEY,
  asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  timestamp TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL,
  sentiment_score DECIMAL(5, 4),
  positive_count INT DEFAULT 0,
  negative_count INT DEFAULT 0,
  neutral_count INT DEFAULT 0,
  volume_mentions INT DEFAULT 0,
  top_keywords TEXT[],
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sentiment_asset_time ON sentiment_data(asset_id, timestamp DESC);
CREATE INDEX idx_sentiment_source ON sentiment_data(source, timestamp DESC);

CREATE TABLE IF NOT EXISTS technical_indicators (
  id SERIAL PRIMARY KEY,
  asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  timestamp TIMESTAMPTZ NOT NULL,
  interval TEXT NOT NULL DEFAULT '1h',
  rsi_14 DECIMAL(10, 4),
  rsi_7 DECIMAL(10, 4),
  macd DECIMAL(20, 8),
  macd_signal DECIMAL(20, 8),
  macd_histogram DECIMAL(20, 8),
  sma_20 DECIMAL(20, 8),
  sma_50 DECIMAL(20, 8),
  sma_200 DECIMAL(20, 8),
  ema_12 DECIMAL(20, 8),
  ema_26 DECIMAL(20, 8),
  bollinger_upper DECIMAL(20, 8),
  bollinger_middle DECIMAL(20, 8),
  bollinger_lower DECIMAL(20, 8),
  stochastic_k DECIMAL(10, 4),
  stochastic_d DECIMAL(10, 4),
  atr DECIMAL(20, 8),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(asset_id, timestamp, interval)
);

CREATE INDEX idx_indicators_asset_time ON technical_indicators(asset_id, timestamp DESC);

CREATE TABLE IF NOT EXISTS predictions (
  id SERIAL PRIMARY KEY,
  asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  prediction_timestamp TIMESTAMPTZ NOT NULL,
  target_timestamp TIMESTAMPTZ NOT NULL,
  model_name TEXT NOT NULL,
  model_version TEXT NOT NULL,
  predicted_price DECIMAL(20, 8) NOT NULL,
  confidence_lower DECIMAL(20, 8),
  confidence_upper DECIMAL(20, 8),
  confidence_level DECIMAL(5, 4) DEFAULT 0.95,
  feature_importance JSONB,
  actual_price DECIMAL(20, 8),
  error_percentage DECIMAL(10, 4),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_predictions_asset ON predictions(asset_id, prediction_timestamp DESC);
CREATE INDEX idx_predictions_target ON predictions(target_timestamp DESC);

CREATE TABLE IF NOT EXISTS alerts (
  id SERIAL PRIMARY KEY,
  asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  alert_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  metadata JSONB,
  triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  acknowledged BOOLEAN DEFAULT FALSE,
  acknowledged_at TIMESTAMPTZ
);

CREATE INDEX idx_alerts_asset ON alerts(asset_id, triggered_at DESC);
CREATE INDEX idx_alerts_acknowledged ON alerts(acknowledged, triggered_at DESC);

CREATE TABLE IF NOT EXISTS correlations (
  id SERIAL PRIMARY KEY,
  asset_id_1 TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  asset_id_2 TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  timestamp TIMESTAMPTZ NOT NULL,
  period_days INT NOT NULL,
  pearson_correlation DECIMAL(10, 8),
  spearman_correlation DECIMAL(10, 8),
  rolling_correlation DECIMAL(10, 8),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(asset_id_1, asset_id_2, timestamp, period_days)
);

CREATE INDEX idx_correlations_assets ON correlations(asset_id_1, asset_id_2, timestamp DESC);

CREATE TABLE IF NOT EXISTS watchlist (
  id SERIAL PRIMARY KEY,
  asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  notes TEXT,
  alert_enabled BOOLEAN DEFAULT TRUE,
  price_alert_threshold DECIMAL(10, 4),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_watchlist_asset ON watchlist(asset_id);

CREATE TABLE IF NOT EXISTS news_articles (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  url TEXT NOT NULL UNIQUE,
  source TEXT,
  image_url TEXT,
  published_at TIMESTAMPTZ NOT NULL,
  sentiment_score DECIMAL(5, 4),
  related_assets TEXT[],
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_news_published ON news_articles(published_at DESC);
CREATE INDEX idx_news_assets ON news_articles USING GIN(related_assets);
