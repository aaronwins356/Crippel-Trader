import React, { useCallback, useEffect, useMemo, useState } from 'react';
import dayjs from 'dayjs';
import {
  Area,
  AreaChart,
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';
import useTradingStream from './hooks/useTradingStream';
import { formatCurrency, formatNumber, formatPercent, classifyChange } from './utils/format';

const COLOR_MAP = {
  'positive-strong': '#22d3ee',
  positive: '#38bdf8',
  neutral: '#64748b',
  negative: '#f97316',
  'negative-strong': '#ef4444'
};

const PIE_COLORS = ['#38bdf8', '#6366f1', '#10b981', '#f97316', '#ef4444'];

const Section = ({ title, subtitle, children, actions }) => (
  <section className="panel">
    <header className="panel__header">
      <div>
        <h2>{title}</h2>
        {subtitle && <span className="panel__subtitle">{subtitle}</span>}
      </div>
      {actions && <div className="panel__actions">{actions}</div>}
    </header>
    <div className="panel__body">{children}</div>
  </section>
);

const HeatCell = ({ asset }) => (
  <div className={`heat-cell heat-cell--${classifyChange(asset.changePercent)}`}>
    <span className="heat-cell__symbol">{asset.symbol}</span>
    <span className="heat-cell__value">{formatPercent(asset.changePercent)}</span>
  </div>
);

const StrategyEvent = ({ event }) => (
  <li className="strategy-event">
    <div>
      <span className="strategy-event__symbol">{event.symbol}</span>
      <span className={`strategy-event__action strategy-event__action--${event.action.toLowerCase()}`}>
        {event.action}
      </span>
    </div>
    <div className="strategy-event__meta">
      <span>{dayjs(event.timestamp).format('HH:mm:ss')}</span>
      <span>{formatNumber(event.price)}</span>
      {event.rsi && <span>RSI {formatNumber(event.rsi)}</span>}
    </div>
  </li>
);

const App = () => {
  const [market, setMarket] = useState([]);
  const [analytics, setAnalytics] = useState({ assets: [], leaders: [], laggards: [], riskBuckets: {} });
  const [portfolio, setPortfolio] = useState(null);
  const [strategyLog, setStrategyLog] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState('BTC-USD');
  const [history, setHistory] = useState([]);

  const fetchHistory = useCallback(async (symbol) => {
    try {
      const response = await fetch(`/api/history/${symbol}`);
      if (!response.ok) return;
      const data = await response.json();
      setHistory((data?.candles || []).map((item) => ({
        time: dayjs(item.timestamp).format('HH:mm'),
        ...item
      })));
    } catch (error) {
      console.error('Failed to load history', error);
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [analyticsRes, portfolioRes, ordersRes, strategyRes] = await Promise.all([
        fetch('/api/analytics').then((res) => res.json()),
        fetch('/api/portfolio').then((res) => res.json()),
        fetch('/api/orders').then((res) => res.json()),
        fetch('/api/strategy/log').then((res) => res.json())
      ]);
      setAnalytics(analyticsRes || { assets: [], leaders: [], laggards: [], riskBuckets: {} });
      const resolvedPortfolio = portfolioRes
        ? { ...portfolioRes, trades: ordersRes.trades || [] }
        : null;
      setPortfolio(resolvedPortfolio);
      setStrategyLog(strategyRes.log || []);
    } catch (error) {
      console.error('Failed to refresh snapshot', error);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    fetchHistory(selectedSymbol);
  }, [selectedSymbol, fetchHistory]);

  const handleStreamPayload = useCallback((payload) => {
    if (payload.type !== 'market:update') return;
    setMarket(payload.market || []);
    setAnalytics(payload.analytics || { assets: [], leaders: [], laggards: [], riskBuckets: {} });
    setPortfolio(payload.portfolio || null);
    setStrategyLog(payload.strategy?.log || []);
    const existing = payload.market?.find((asset) => asset.symbol === selectedSymbol);
    if (!existing && payload.market?.length) {
      setSelectedSymbol(payload.market[0].symbol);
    }
    if (existing) {
      setHistory((prev) => {
        if (!prev.length) return prev;
        const last = prev[prev.length - 1];
        if (last && dayjs(last.timestamp).isSame(existing.lastUpdate)) {
          return prev;
        }
        const nextPoint = {
          time: dayjs(existing.lastUpdate).format('HH:mm'),
          timestamp: existing.lastUpdate,
          open: last.close,
          high: Math.max(last.close, existing.price),
          low: Math.min(last.close, existing.price),
          close: existing.price,
          volume: Math.abs(existing.change || 0) * 35
        };
        return [...prev.slice(-239), nextPoint];
      });
    }
  }, [selectedSymbol]);

  useTradingStream(handleStreamPayload);

  const selectedAnalytics = useMemo(() => (
    analytics.assets?.find((asset) => asset.symbol === selectedSymbol) || null
  ), [analytics, selectedSymbol]);

  const allocationData = useMemo(() => {
    if (!portfolio?.positions?.length) {
      return [{ name: 'Cash', value: portfolio ? portfolio.cash : 1 }];
    }
    const slices = portfolio.positions
      .filter((position) => Math.abs(position.marketValue) > 0.01)
      .map((position) => ({
        name: position.symbol,
        value: Math.abs(position.marketValue)
      }));
    return [...slices, { name: 'Cash', value: portfolio.cash }];
  }, [portfolio]);

  const exposureSeries = useMemo(() => {
    const data = analytics.assets || [];
    return data.map((item) => ({
      symbol: item.symbol,
      change: item.changePercent,
      rsi: item.rsi || 0
    }));
  }, [analytics]);

  const leaders = analytics.leaders || [];
  const laggards = analytics.laggards || [];

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>Crippel Trader</h1>
          <p>Automated multi-asset execution with real-time quantitative analytics</p>
        </div>
        {portfolio && (
          <div className="app-header__metrics">
            <div>
              <span>Equity</span>
              <strong>{formatCurrency(portfolio.equity)}</strong>
            </div>
            <div>
              <span>Cash</span>
              <strong>{formatCurrency(portfolio.cash)}</strong>
            </div>
            <div>
              <span>Realized PnL</span>
              <strong className={`tag tag--${portfolio.realizedPnL >= 0 ? 'positive' : 'negative'}`}>
                {formatCurrency(portfolio.realizedPnL)}
              </strong>
            </div>
          </div>
        )}
      </header>

      <main className="dashboard-grid">
        <Section
          title="Market Depth"
          subtitle={selectedAnalytics ? `${selectedAnalytics.name}` : 'Selecting...'}
          actions={(
            <select value={selectedSymbol} onChange={(event) => setSelectedSymbol(event.target.value)}>
              {market.map((asset) => (
                <option key={asset.symbol} value={asset.symbol}>
                  {asset.symbol}
                </option>
              ))}
            </select>
          )}
        >
          <div className="chart-block">
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={history} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="priceGradient" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.7} />
                    <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="time" stroke="rgba(255,255,255,0.4)" minTickGap={25} />
                <YAxis stroke="rgba(255,255,255,0.4)" domain={['auto', 'auto']} />
                <Tooltip contentStyle={{ background: '#111827', borderRadius: 8, border: 'none' }} />
                <Area type="monotone" dataKey="close" stroke="#38bdf8" fill="url(#priceGradient)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          {selectedAnalytics && (
            <div className="metrics-bar">
              <div>
                <span>RSI</span>
                <strong>{formatNumber(selectedAnalytics.rsi || 0)}</strong>
              </div>
              <div>
                <span>SMA 21</span>
                <strong>{formatNumber(selectedAnalytics.sma21 || 0)}</strong>
              </div>
              <div>
                <span>SMA 50</span>
                <strong>{formatNumber(selectedAnalytics.sma50 || 0)}</strong>
              </div>
              <div>
                <span>Volatility</span>
                <strong>{formatNumber(selectedAnalytics.volatility || 0)}</strong>
              </div>
              <div>
                <span>Drawdown</span>
                <strong>{formatPercent(-(selectedAnalytics.drawdown || 0))}</strong>
              </div>
            </div>
          )}
        </Section>

        <Section title="Leaders & Laggards" subtitle="24h performance dispersion">
          <div className="leaders-grid">
            <div>
              <h3>Leaders</h3>
              <div className="heat-grid">
                {leaders.map((asset) => (
                  <HeatCell key={asset.symbol} asset={asset} />
                ))}
              </div>
            </div>
            <div>
              <h3>Laggards</h3>
              <div className="heat-grid heat-grid--inverse">
                {laggards.map((asset) => (
                  <HeatCell key={asset.symbol} asset={asset} />
                ))}
              </div>
            </div>
          </div>
        </Section>

        <Section title="Portfolio Allocation" subtitle="Gross exposure by asset">
          <div className="chart-block">
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie dataKey="value" data={allocationData} innerRadius={60} outerRadius={90} paddingAngle={4}>
                  {allocationData.map((entry, index) => (
                    <Cell key={`slice-${entry.name}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value, name) => [formatCurrency(value), name]}
                  contentStyle={{ background: '#111827', border: 'none', borderRadius: 8 }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          {portfolio && (
            <div className="metrics-bar">
              <div>
                <span>Net Exposure</span>
                <strong>{formatCurrency(portfolio.netExposure)}</strong>
              </div>
              <div>
                <span>Gross Exposure</span>
                <strong>{formatCurrency(portfolio.grossExposure)}</strong>
              </div>
              <div>
                <span>Leverage</span>
                <strong>{formatNumber(portfolio.leverage)}</strong>
              </div>
            </div>
          )}
        </Section>

        <Section title="Momentum Monitor" subtitle="Change vs RSI signal strength">
          <div className="chart-block">
            <ResponsiveContainer width="100%" height={220}>
              <ComposedChart data={exposureSeries}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis dataKey="symbol" stroke="rgba(255,255,255,0.4)" />
                <YAxis yAxisId="left" stroke="rgba(255,255,255,0.4)" />
                <YAxis yAxisId="right" orientation="right" stroke="rgba(250,204,21,0.75)" />
                <Tooltip contentStyle={{ background: '#111827', borderRadius: 8, border: 'none' }} />
                <Bar dataKey="change" radius={6} yAxisId="left">
                  {exposureSeries.map((entry) => {
                    const bucket = classifyChange(entry.change);
                    return <Cell key={entry.symbol} fill={COLOR_MAP[bucket]} />;
                  })}
                </Bar>
                <Line type="monotone" dataKey="rsi" stroke="#facc15" strokeWidth={2} dot={false} yAxisId="right" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </Section>

        <Section title="Order Blotter" subtitle="Most recent executions">
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Symbol</th>
                  <th>Qty</th>
                  <th>Price</th>
                  <th>Cost</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {portfolio?.trades?.slice(-10).reverse().map((trade) => (
                  <tr key={trade.id}>
                    <td>{dayjs(trade.timestamp).format('HH:mm:ss')}</td>
                    <td>{trade.symbol}</td>
                    <td className={trade.quantity >= 0 ? 'positive' : 'negative'}>{formatNumber(trade.quantity)}</td>
                    <td>{formatNumber(trade.price)}</td>
                    <td>{formatCurrency(trade.cost)}</td>
                    <td>{trade.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>

        <Section title="Strategy Timeline" subtitle="Signal diagnostics">
          <ul className="strategy-feed">
            {strategyLog.slice(-8).reverse().map((event) => (
              <StrategyEvent key={event.id} event={event} />
            ))}
          </ul>
        </Section>
      </main>
    </div>
  );
};

export default App;
