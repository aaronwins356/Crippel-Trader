import React, { useEffect, useMemo, useState } from 'react';
import useSWR from 'swr';

import KPI from '../components/KPI';
import ModeToggle from '../components/ModeToggle';
import AggressionSlider from '../components/AggressionSlider';
import EquityChart from '../components/EquityChart';
import OrderBlotter from '../components/OrderBlotter';
import ConnectionIndicator from '../components/ConnectionIndicator';
import { endpoints } from '../lib/api';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export default function Dashboard() {
  const { data: settings } = useSWR('/api/settings', endpoints.settings, { refreshInterval: 15000 });
  const { data: stats } = useSWR('/api/stats', endpoints.stats, { refreshInterval: 5000 });
  const [mode, setMode] = useState('paper');
  const [aggression, setAggression] = useState(3);
  const [trades, setTrades] = useState([]);
  const [equitySeries, setEquitySeries] = useState([]);
  const [connection, setConnection] = useState('connecting');

  useEffect(() => {
    if (settings) {
      setMode(settings.mode);
      setAggression(settings.aggression);
    }
  }, [settings]);

  useEffect(() => {
    const url = BACKEND_URL.replace('http', 'ws') + '/ws/stream';
    const ws = new WebSocket(url);
    setConnection('connecting');
    ws.onopen = () => setConnection('connected');
    ws.onclose = () => setConnection('disconnected');
    ws.onerror = () => setConnection('disconnected');
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.channel === 'trade') {
          setTrades((prev) => [message.payload, ...prev].slice(0, 30));
        }
        if (message.channel === 'portfolio:update') {
          setEquitySeries((prev) => [...prev.slice(-199), message.payload]);
        }
        if (message.channel === 'mode:update') {
          setMode(message.payload.mode);
        }
      } catch (error) {
        console.error('WS parse error', error);
      }
    };
    return () => {
      ws.close();
    };
  }, []);

  const pnlValue = stats ? `${stats.pnl.toFixed(2)} USD` : '…';
  const winRateValue = stats ? `${(stats.win_rate * 100).toFixed(1)} %` : '…';
  const equityValue = stats && typeof stats.equity === 'number' ? `${stats.equity.toFixed(2)} USD` : '…';
  const cashValue = stats && typeof stats.cash === 'number' ? `${stats.cash.toFixed(2)} USD` : '…';

  const handleAggressionChange = async (level) => {
    setAggression(level);
    await fetch(`${BACKEND_URL}/api/settings/aggression?aggression=${level}`, { method: 'POST' });
  };

  const handleToggleMode = async () => {
    const nextMode = mode === 'live' ? 'paper' : 'live';
    if (nextMode === 'live') {
      const confirmed = window.confirm('Enable LIVE trading? This will route orders to the exchange.');
      if (!confirmed) {
        return;
      }
      await fetch(`${BACKEND_URL}/api/mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'live', confirm: true })
      });
      setMode('live');
    } else {
      await fetch(`${BACKEND_URL}/api/mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'paper', confirm: false })
      });
      setMode('paper');
    }
  };

  const kpis = useMemo(() => (
    [
      { title: 'Realized + Unrealized PnL', value: pnlValue },
      { title: 'Win Rate', value: winRateValue },
      { title: 'Total Trades', value: stats ? stats.total_trades : '…' },
      { title: 'Cash', value: cashValue },
      { title: 'Equity', value: equityValue }
    ]
  ), [pnlValue, winRateValue, stats, cashValue, equityValue]);

  return (
    <main className="dashboard">
      <ConnectionIndicator status={connection} />
      <ModeToggle mode={mode} onToggle={handleToggleMode} />
      <AggressionSlider value={aggression} onChange={handleAggressionChange} />
      {kpis.map((kpi) => (
        <KPI key={kpi.title} title={kpi.title} value={kpi.value} />
      ))}
      <EquityChart data={equitySeries} />
      <OrderBlotter trades={trades} />
    </main>
  );
}
