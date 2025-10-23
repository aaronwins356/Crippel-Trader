import React, { useMemo } from 'react';
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer
} from 'recharts';
import { formatCurrency } from '../utils/format.js';

const PIE_COLORS = ['#38bdf8', '#6366f1', '#0ea5e9', '#10b981', '#f97316', '#f59e0b'];

const PositionRow = ({ position }) => (
  <tr>
    <td>{position.symbol}</td>
    <td>{position.quantity}</td>
    <td>{formatCurrency(position.avgPrice)}</td>
    <td>{formatCurrency(position.latestPrice)}</td>
    <td>{formatCurrency(position.marketValue)}</td>
    <td className={position.unrealizedPnL >= 0 ? 'text-positive' : 'text-negative'}>
      {formatCurrency(position.unrealizedPnL)}
    </td>
  </tr>
);

const TradeRow = ({ trade }) => (
  <tr>
    <td>{new Date(trade.timestamp).toLocaleTimeString()}</td>
    <td>{trade.symbol}</td>
    <td className={trade.quantity > 0 ? 'text-positive' : 'text-negative'}>{trade.quantity}</td>
    <td>{formatCurrency(trade.price)}</td>
    <td>{trade.reason}</td>
  </tr>
);

const PortfolioPanel = ({ portfolio }) => {
  const allocation = useMemo(() => {
    if (!portfolio) return [];
    const slices = (portfolio.positions || [])
      .filter((position) => Math.abs(position.marketValue) > 1)
      .map((position) => ({
        name: position.symbol,
        value: Math.abs(position.marketValue)
      }));
    if (portfolio.cash > 0) {
      slices.push({ name: 'Cash', value: portfolio.cash });
    }
    return slices;
  }, [portfolio]);

  const leveragePercent = Math.min(100, Math.round((portfolio?.leverage ?? 0) * 33));

  return (
    <section className="panel">
      <header className="panel__header">
        <div>
          <h2>Portfolio Intelligence</h2>
          <span className="panel__subtitle">Positions, execution tape, and balance sheet telemetry</span>
        </div>
      </header>
      <div className="panel__body portfolio-panel">
        <div className="portfolio-panel__allocation">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={allocation} dataKey="value" nameKey="name" innerRadius={50} outerRadius={90} paddingAngle={4}>
                {allocation.map((entry, index) => (
                  <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                ))}
              </Pie>
              <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle" fill="#e2e8f0" fontSize="16px">
                {portfolio ? formatCurrency(portfolio.equity) : '–'}
              </text>
            </PieChart>
          </ResponsiveContainer>
          <div className="portfolio-panel__gauges">
            <div className="gauge">
              <span>Leverage</span>
              <div className="gauge__bar">
                <div className="gauge__fill" style={{ width: `${leveragePercent}%` }} />
              </div>
              <strong>{portfolio?.leverage?.toFixed(2) ?? '0.00'}x</strong>
            </div>
            <div className="gauge">
              <span>Net Exposure</span>
              <div className="gauge__bar">
                <div
                  className={`gauge__fill gauge__fill--${portfolio?.netExposure >= 0 ? 'positive' : 'negative'}`}
                  style={{ width: `${Math.min(100, Math.abs(portfolio?.netExposure || 0) / (portfolio?.equity || 1) * 100)}%` }}
                />
              </div>
              <strong>{portfolio ? formatCurrency(portfolio.netExposure) : '–'}</strong>
            </div>
          </div>
        </div>
        <div className="portfolio-panel__positions">
          <h3>Active Positions</h3>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Qty</th>
                  <th>Avg Price</th>
                  <th>Mark</th>
                  <th>Market Value</th>
                  <th>Unrealized</th>
                </tr>
              </thead>
              <tbody>
                {portfolio?.positions?.length ? (
                  portfolio.positions.map((position) => <PositionRow key={position.symbol} position={position} />)
                ) : (
                  <tr>
                    <td colSpan={6} className="text-muted">No open positions</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
        <div className="portfolio-panel__trades">
          <h3>Execution Tape</h3>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Symbol</th>
                  <th>Qty</th>
                  <th>Price</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {portfolio?.trades?.length ? (
                  portfolio.trades
                    .slice(-20)
                    .reverse()
                    .map((trade) => <TradeRow key={trade.id} trade={trade} />)
                ) : (
                  <tr>
                    <td colSpan={5} className="text-muted">No executions yet</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
};

export default PortfolioPanel;
