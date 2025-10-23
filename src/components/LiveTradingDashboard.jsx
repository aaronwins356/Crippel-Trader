import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import useTradingStream from '../hooks/useTradingStream.js';
import { formatCurrency, formatNumber } from '../utils/format.js';

const timestampLabel = (value) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

const LiveTradingDashboard = ({ active }) => {
  const [liveState, setLiveState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchLiveState = useCallback(async () => {
    if (!active) return;
    try {
      setLoading(true);
      const response = await fetch('/api/live/state');
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || 'Failed to load live trading state');
      }
      setLiveState(data.state || data);
      setError(null);
    } catch (err) {
      console.error('Failed to load live trading state', err);
      setError(err.message || 'Failed to load live trading state');
    } finally {
      setLoading(false);
    }
  }, [active]);

  useEffect(() => {
    if (!active) return;
    fetchLiveState();
    const interval = setInterval(() => {
      fetchLiveState();
    }, 15000);
    return () => clearInterval(interval);
  }, [active, fetchLiveState]);

  useTradingStream(
    useCallback((payload) => {
      if (!active || payload?.type !== 'live:update') return;
      setLiveState(payload.state);
    }, [active]),
    { enabled: active }
  );

  const performanceData = useMemo(() => (
    (liveState?.performance || []).map((entry) => ({
      ...entry,
      label: timestampLabel(entry.timestamp)
    }))
  ), [liveState]);

  const trades = useMemo(() => liveState?.trades?.slice(0, 12) || [], [liveState]);
  const openPositions = liveState?.openPositions || [];
  const brain = liveState?.brain || {};
  const workers = liveState?.workers || [];
  const executor = liveState?.executor || {};
  const research = liveState?.research || [];
  const capital = liveState?.capital || null;

  return (
    <div className="live-dashboard">
      <header className="live-dashboard__header">
        <div>
          <h1>Brain Bot Command Center</h1>
          <p>Brain Bot orchestrates worker cohorts and research intelligence while routing approved orders to the execution stack.</p>
          {liveState?.timestamp && (
            <span className="live-dashboard__timestamp">Last update {new Date(liveState.timestamp).toLocaleTimeString()}</span>
          )}
        </div>
        {capital && (
          <div className="live-dashboard__metrics">
            <div>
              <span>Equity</span>
              <strong>{formatCurrency(capital.equity)}</strong>
            </div>
            <div>
              <span>Cash</span>
              <strong>{formatCurrency(capital.cash)}</strong>
            </div>
            <div>
              <span>Realized P/L</span>
              <strong className={capital.realizedPnL >= 0 ? 'metric-positive' : 'metric-negative'}>
                {formatCurrency(capital.realizedPnL)}
              </strong>
            </div>
            <div>
              <span>Unrealized P/L</span>
              <strong className={capital.unrealizedPnL >= 0 ? 'metric-positive' : 'metric-negative'}>
                {formatCurrency(capital.unrealizedPnL)}
              </strong>
            </div>
          </div>
        )}
      </header>

      {error && <div className="live-dashboard__error">{error}</div>}

      {loading && !liveState ? (
        <div className="live-dashboard__loading">Loading live trading intelligence…</div>
      ) : (
        <div className="live-grid">
          <section className="live-grid__panel live-grid__panel--brain">
            <h2>Brain Bot</h2>
            <p className="live-grid__status">Status: <strong>{brain.status || 'initializing'}</strong></p>
            <div className="live-grid__directives">
              <h3>Directives</h3>
              <ul>
                {(brain.directives || []).map((directive) => (
                  <li key={directive}>{directive}</li>
                ))}
              </ul>
            </div>
            {brain.activeSignals?.length ? (
              <div className="live-grid__signals">
                <h3>Active Signals</h3>
                <ul>
                  {brain.activeSignals.map((signal) => (
                    <li key={signal}>{signal}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            <div className="live-grid__research">
              <h3>Research Feed</h3>
              <ul>
                {research.slice(0, 6).map((note) => (
                  <li key={note.id}>
                    <strong>{note.author}</strong>
                    <span>{timestampLabel(note.timestamp)}</span>
                    <p>{note.theme} — {note.catalyst}</p>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section className="live-grid__panel live-grid__panel--workers">
            <h2>Worker Pods</h2>
            <ul>
              {workers.map((worker) => (
                <li key={worker.id}>
                  <div className="worker-name">{worker.name}</div>
                  <div className="worker-focus">{worker.focus}</div>
                  <div className={`worker-status worker-status--${worker.status?.replace(/\s+/g, '-') || 'idle'}`}>
                    {worker.status || 'idle'}
                  </div>
                  <div className="worker-confidence">Confidence {formatNumber(worker.confidence || 0, { maximumFractionDigits: 1 })}%</div>
                  {worker.lastSignal && (
                    <div className="worker-last-signal">
                      <span>{worker.lastSignal.symbol} {worker.lastSignal.side.toUpperCase()} @ {formatNumber(worker.lastSignal.price)}</span>
                      <small>{timestampLabel(worker.lastSignal.timestamp)}</small>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </section>

          <section className="live-grid__panel live-grid__panel--executor">
            <h2>Executor</h2>
            <p>Status: <strong>{executor.status || 'idle'}</strong></p>
            <p>Mode: <strong>{executor.mode === 'live' ? 'Kraken API' : 'Simulation'}</strong></p>
            {executor.lastOrderReference && <p>Last order ref: <code>{executor.lastOrderReference}</code></p>}
            {executor.lastDecision && (
              <div className="executor-decision">
                <h3>Last Decision</h3>
                <p><strong>{executor.lastDecision.workerName || executor.lastDecision.workerId}</strong> proposed {executor.lastDecision.side?.toUpperCase()} {executor.lastDecision.quantity} {executor.lastDecision.symbol} at {formatNumber(executor.lastDecision.price)}.</p>
                <p>{executor.lastDecision.narrative}</p>
                <small>{timestampLabel(executor.lastDecision.timestamp)}</small>
                {executor.lastDecision.error && <p className="executor-error">{executor.lastDecision.error}</p>}
              </div>
            )}
          </section>

          <section className="live-grid__panel live-grid__panel--performance">
            <h2>P/L Performance</h2>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={performanceData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
                <XAxis dataKey="label" minTickGap={32} />
                <YAxis tickFormatter={(value) => formatNumber(value, { maximumFractionDigits: 0 })} />
                <Tooltip formatter={(value) => formatCurrency(value)} labelFormatter={(label) => `Snapshot ${label}`} />
                <Legend />
                <Line type="monotone" dataKey="equity" stroke="#4c6ef5" strokeWidth={2} dot={false} name="Equity" />
                <Line type="monotone" dataKey="realized" stroke="#37b24d" strokeWidth={1.5} dot={false} name="Realized" />
                <Line type="monotone" dataKey="unrealized" stroke="#f59f00" strokeWidth={1.5} dot={false} name="Unrealized" />
              </LineChart>
            </ResponsiveContainer>
          </section>

          <section className="live-grid__panel live-grid__panel--positions">
            <h2>Open Positions</h2>
            {openPositions.length === 0 ? (
              <p className="live-grid__empty">No active positions</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Direction</th>
                    <th>Quantity</th>
                    <th>Avg Price</th>
                    <th>Last Price</th>
                    <th>Unrealized P/L</th>
                  </tr>
                </thead>
                <tbody>
                  {openPositions.map((position) => (
                    <tr key={position.symbol}>
                      <td>{position.symbol}</td>
                      <td className={`direction direction--${position.direction}`}>{position.direction}</td>
                      <td>{formatNumber(position.quantity)}</td>
                      <td>{formatNumber(position.avgPrice)}</td>
                      <td>{formatNumber(position.lastPrice)}</td>
                      <td className={position.unrealizedPnl >= 0 ? 'metric-positive' : 'metric-negative'}>
                        {formatCurrency(position.unrealizedPnl)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section className="live-grid__panel live-grid__panel--trades">
            <h2>Recent Trades</h2>
            {trades.length === 0 ? (
              <p className="live-grid__empty">No trades submitted yet</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Worker</th>
                    <th>Symbol</th>
                    <th>Side</th>
                    <th>Qty</th>
                    <th>Price</th>
                    <th>Confidence</th>
                    <th>Execution</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.map((trade) => (
                    <tr key={trade.id}>
                      <td>{timestampLabel(trade.timestamp)}</td>
                      <td>{trade.workerName || trade.workerId}</td>
                      <td>{trade.symbol}</td>
                      <td className={`direction direction--${trade.side}`}>{trade.side.toUpperCase()}</td>
                      <td>{formatNumber(trade.quantity)}</td>
                      <td>{formatNumber(trade.price)}</td>
                      <td>{formatNumber(trade.confidence || 0)}%</td>
                      <td>{trade.execution?.reference || trade.execution?.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </div>
      )}
    </div>
  );
};

export default LiveTradingDashboard;
