import React, { useMemo } from 'react';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';
import { formatNumber, formatPercent } from '../utils/format.js';

const StrategyEvent = ({ event }) => (
  <li className="strategy-event">
    <div className="strategy-event__header">
      <span className="strategy-event__symbol">{event.symbol}</span>
      <span className={`strategy-event__action strategy-event__action--${event.action?.toLowerCase()}`}>{event.action}</span>
    </div>
    <div className="strategy-event__meta">
      <span>{new Date(event.timestamp).toLocaleTimeString()}</span>
      <span>Px {formatNumber(event.price)}</span>
      {event.rsi && <span>RSI {formatNumber(event.rsi)}</span>}
    </div>
  </li>
);

const RiskBucket = ({ label, assets }) => (
  <div className="risk-bucket">
    <h4>{label}</h4>
    <ul>
      {assets.length ? assets.map((asset) => (
        <li key={asset.symbol}>
          <span>{asset.symbol}</span>
          <strong>{asset.volatility ? formatNumber(asset.volatility) : '–'}</strong>
        </li>
      )) : <li className="text-muted">No assets</li>}
    </ul>
  </div>
);

const AnalyticsPanel = ({ analytics, strategyLog }) => {
  const chartData = useMemo(() => (analytics?.assets || []).map((asset) => ({
    symbol: asset.symbol,
    change: asset.changePercent || 0,
    rsi: asset.rsi || 0
  })), [analytics]);

  return (
    <section className="panel analytics-panel">
      <header className="panel__header">
        <div>
          <h2>Alpha Radar</h2>
          <span className="panel__subtitle">Momentum dispersion, risk clustering, and strategy telemetry</span>
        </div>
      </header>
      <div className="panel__body analytics-panel__body">
        <div className="analytics-panel__chart">
          <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.15)" />
              <XAxis dataKey="symbol" stroke="rgba(226,232,240,0.6)" />
              <YAxis yAxisId="left" orientation="left" stroke="rgba(226,232,240,0.6)" tickFormatter={(value) => `${value.toFixed(1)}%`} />
              <YAxis yAxisId="right" orientation="right" stroke="rgba(226,232,240,0.6)" tickFormatter={(value) => value.toFixed(0)} />
              <Tooltip formatter={(value, name) => [name === 'change' ? formatPercent(value) : formatNumber(value), name === 'change' ? 'Δ' : 'RSI']} />
              <Bar yAxisId="left" dataKey="change" barSize={16} fill="rgba(56,189,248,0.8)" radius={[4, 4, 0, 0]} />
              <Line yAxisId="right" type="monotone" dataKey="rsi" stroke="#f97316" strokeWidth={2} dot={{ r: 2 }} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <div className="analytics-panel__leaders">
          <div>
            <h3>Leaders</h3>
            <ul>
              {(analytics?.leaders || []).map((asset) => (
                <li key={asset.symbol}>
                  <span>{asset.symbol}</span>
                  <strong>{formatPercent(asset.changePercent ?? 0)}</strong>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3>Laggards</h3>
            <ul>
              {(analytics?.laggards || []).map((asset) => (
                <li key={asset.symbol}>
                  <span>{asset.symbol}</span>
                  <strong>{formatPercent(asset.changePercent ?? 0)}</strong>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="analytics-panel__risk">
          <RiskBucket label="Very High" assets={analytics?.riskBuckets?.veryHigh || []} />
          <RiskBucket label="High" assets={analytics?.riskBuckets?.high || []} />
          <RiskBucket label="Medium" assets={analytics?.riskBuckets?.medium || []} />
          <RiskBucket label="Low" assets={analytics?.riskBuckets?.low || []} />
        </div>
        <div className="analytics-panel__log">
          <h3>Strategy Log</h3>
          <ul>
            {strategyLog?.length ? strategyLog.slice(0, 12).map((event) => (
              <StrategyEvent key={event.tradeId} event={event} />
            )) : <li className="text-muted">Awaiting strategy signals</li>}
          </ul>
        </div>
      </div>
    </section>
  );
};

export default AnalyticsPanel;
