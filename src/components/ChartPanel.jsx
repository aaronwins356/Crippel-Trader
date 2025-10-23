import React, { useMemo } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';
import { formatCurrency, formatNumber, formatPercent } from '../utils/format.js';

const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  const data = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{label}</strong>
      <div>Price: {formatCurrency(data.close)}</div>
      {data.ema21 && <div>EMA 21: {formatNumber(data.ema21)}</div>}
      {data.ema100 && <div>EMA 100: {formatNumber(data.ema100)}</div>}
      {data.rsi && <div>RSI: {formatNumber(data.rsi)}</div>}
    </div>
  );
};

const ChartPanel = ({ history, assets, analytics, selectedSymbol, onSymbolChange }) => {
  const indicatorMetrics = useMemo(() => {
    if (!analytics) return null;
    const { rsi, ema21, ema100, macd, bollinger, volatility, drawdown, changePercent } = analytics;
    return {
      rsi,
      ema21,
      ema100,
      macd,
      bollinger,
      volatility,
      drawdown,
      changePercent
    };
  }, [analytics]);

  const chartData = useMemo(() => history.map((point) => ({
    ...point,
    time: point.time || new Date(point.timestamp).toLocaleTimeString(),
    ema21: analytics?.ema21,
    ema100: analytics?.ema100,
    rsi: analytics?.rsi
  })), [history, analytics]);

  return (
    <section className="panel panel--primary">
      <header className="panel__header">
        <div>
          <h2>Market Structure</h2>
          <span className="panel__subtitle">Live synthetic candle stream and momentum overlays</span>
        </div>
        <div className="panel__actions">
          <select value={selectedSymbol} onChange={(event) => onSymbolChange(event.target.value)}>
            {assets.map((asset) => (
              <option key={asset.symbol} value={asset.symbol}>
                {asset.symbol} — {asset.name}
              </option>
            ))}
          </select>
        </div>
      </header>
      <div className="panel__body">
        <div className="chart-block">
          <ResponsiveContainer width="100%" height={360}>
            <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.5} />
                  <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="4 4" stroke="rgba(148, 163, 184, 0.15)" />
              <XAxis dataKey="time" stroke="rgba(226, 232, 240, 0.55)" hide={chartData.length > 120} />
              <YAxis stroke="rgba(226, 232, 240, 0.55)" domain={['auto', 'auto']} tickFormatter={(value) => formatNumber(value)} />
              <Tooltip content={<ChartTooltip />} />
              <Area type="monotone" dataKey="close" stroke="#38bdf8" fill="url(#priceGradient)" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="ema21" stroke="#6366f1" strokeWidth={1.5} dot={false} />
              <Line type="monotone" dataKey="ema100" stroke="#f97316" strokeWidth={1.5} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        {indicatorMetrics && (
          <div className="metrics-bar">
            <div>
              <span>RSI</span>
              <strong>{indicatorMetrics.rsi ? formatNumber(indicatorMetrics.rsi) : '–'}</strong>
            </div>
            <div>
              <span>EMA 21</span>
              <strong>{indicatorMetrics.ema21 ? formatNumber(indicatorMetrics.ema21) : '–'}</strong>
            </div>
            <div>
              <span>EMA 100</span>
              <strong>{indicatorMetrics.ema100 ? formatNumber(indicatorMetrics.ema100) : '–'}</strong>
            </div>
            <div>
              <span>MACD</span>
              <strong>
                {indicatorMetrics.macd
                  ? `${formatNumber(indicatorMetrics.macd.macd)} / ${formatNumber(indicatorMetrics.macd.signal)}`
                  : '–'}
              </strong>
            </div>
            <div>
              <span>Volatility</span>
              <strong>{indicatorMetrics.volatility ? formatNumber(indicatorMetrics.volatility) : '–'}</strong>
            </div>
            <div>
              <span>Drawdown</span>
              <strong>{indicatorMetrics.drawdown ? formatPercent(indicatorMetrics.drawdown, { maximumFractionDigits: 1 }) : '–'}</strong>
            </div>
            <div>
              <span>Session Change</span>
              <strong>{indicatorMetrics.changePercent != null ? formatPercent(indicatorMetrics.changePercent) : '–'}</strong>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};

export default ChartPanel;
