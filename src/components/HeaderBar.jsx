import React from 'react';
import { formatCurrency } from '../utils/format.js';

const MetricTile = ({ label, value, accent }) => (
  <div className={`metric-tile metric-tile--${accent || 'neutral'}`}>
    <span>{label}</span>
    <strong>{value}</strong>
  </div>
);

const HeaderBar = ({ portfolio, timestamp }) => (
  <header className="app-header">
    <div>
      <h1>Crippel Trader v2.0</h1>
      <p>Institutional-grade synthetic execution desk with live analytics and automated trade intelligence.</p>
      {timestamp && <span className="app-header__timestamp">Last sync {new Date(timestamp).toLocaleTimeString()}</span>}
    </div>
    {portfolio && (
      <div className="app-header__metrics">
        <MetricTile label="Equity" value={formatCurrency(portfolio.equity)} />
        <MetricTile label="Cash" value={formatCurrency(portfolio.cash)} />
        <MetricTile
          label="Realized PnL"
          value={formatCurrency(portfolio.realizedPnL)}
          accent={portfolio.realizedPnL >= 0 ? 'positive' : 'negative'}
        />
        <MetricTile
          label="Gross Exposure"
          value={formatCurrency(portfolio.grossExposure)}
        />
        <MetricTile
          label="Net Exposure"
          value={formatCurrency(portfolio.netExposure)}
          accent={portfolio.netExposure >= 0 ? 'positive' : 'negative'}
        />
        <MetricTile label="Leverage" value={`${portfolio.leverage?.toFixed(2) ?? '0.00'}x`} />
      </div>
    )}
  </header>
);

export default HeaderBar;
