import React, { useCallback, useEffect, useMemo, useState } from 'react';
import dayjs from 'dayjs';
import HeaderBar from './HeaderBar.jsx';
import ChartPanel from './ChartPanel.jsx';
import PortfolioPanel from './PortfolioPanel.jsx';
import AnalyticsPanel from './AnalyticsPanel.jsx';
import TradeControls from './TradeControls.jsx';
import useTradingStream from '../hooks/useTradingStream.js';

const DEFAULT_HISTORY_LENGTH = 240;

const normaliseHistory = (candles) => candles.map((item) => ({
  ...item,
  time: dayjs(item.timestamp).format('HH:mm')
}));

const PaperTradingDashboard = ({ active }) => {
  const [assets, setAssets] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [portfolio, setPortfolio] = useState(null);
  const [strategyLog, setStrategyLog] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState('BTC-USD');
  const [history, setHistory] = useState([]);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [orderPending, setOrderPending] = useState(false);

  const fetchAssets = useCallback(async () => {
    if (!active) return;
    const response = await fetch('/api/assets');
    const data = await response.json();
    setAssets(data.assets || []);
    if (data.assets?.length && !data.assets.find((asset) => asset.symbol === selectedSymbol)) {
      setSelectedSymbol(data.assets[0].symbol);
    }
  }, [active, selectedSymbol]);

  const fetchHistory = useCallback(async (symbol) => {
    if (!active) return;
    const response = await fetch(`/api/history/${symbol}`);
    const data = await response.json();
    setHistory(normaliseHistory((data?.candles || []).slice(-DEFAULT_HISTORY_LENGTH)));
  }, [active]);

  const bootstrap = useCallback(async () => {
    if (!active) return;
    const [assetsRes, analyticsRes, portfolioRes, ordersRes, strategyRes] = await Promise.all([
      fetch('/api/assets').then((res) => res.json()),
      fetch('/api/analytics').then((res) => res.json()),
      fetch('/api/portfolio').then((res) => res.json()),
      fetch('/api/orders').then((res) => res.json()),
      fetch('/api/strategy/log').then((res) => res.json())
    ]);
    const resolvedAssets = assetsRes.assets || [];
    setAssets(resolvedAssets);
    setAnalytics(analyticsRes);
    setPortfolio(portfolioRes ? { ...portfolioRes, trades: ordersRes.trades || [] } : null);
    setStrategyLog(strategyRes?.log || []);
    setLastUpdate(analyticsRes?.timestamp || new Date().toISOString());
    if (resolvedAssets.length && !resolvedAssets.find((asset) => asset.symbol === selectedSymbol)) {
      setSelectedSymbol(resolvedAssets[0].symbol);
    }
  }, [active, selectedSymbol]);

  useEffect(() => {
    if (!active) return;
    bootstrap().catch((error) => console.error('Failed to bootstrap paper trading state', error));
  }, [active, bootstrap]);

  useEffect(() => {
    if (!active) return;
    fetchHistory(selectedSymbol).catch((error) => console.error('Failed to load history', error));
  }, [active, selectedSymbol, fetchHistory]);

  const handleStreamPayload = useCallback((payload) => {
    if (!active || !payload || payload.type !== 'market:update') return;
    setAssets(payload.market || []);
    setAnalytics(payload.analytics || null);
    setPortfolio(payload.portfolio || null);
    setStrategyLog(payload.strategy?.log || []);
    setLastUpdate(payload.analytics?.timestamp || new Date().toISOString());

    const matchingAsset = payload.analytics?.assets?.find((asset) => asset.symbol === selectedSymbol);
    if (matchingAsset?.latestCandle) {
      setHistory((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.timestamp === matchingAsset.latestCandle.timestamp) {
          return prev;
        }
        const nextPoint = {
          ...matchingAsset.latestCandle,
          time: dayjs(matchingAsset.latestCandle.timestamp).format('HH:mm')
        };
        return [...prev.slice(-(DEFAULT_HISTORY_LENGTH - 1)), nextPoint];
      });
    }

    const symbolExists = payload.market?.find((asset) => asset.symbol === selectedSymbol);
    if (!symbolExists && payload.market?.length) {
      setSelectedSymbol(payload.market[0].symbol);
    }
  }, [active, selectedSymbol]);

  useTradingStream(handleStreamPayload, { enabled: active });

  const selectedAnalytics = useMemo(() => (
    analytics?.assets?.find((asset) => asset.symbol === selectedSymbol) || null
  ), [analytics, selectedSymbol]);

  const handleManualOrder = useCallback(async ({ symbol, quantity, price }) => {
    if (!active) return;
    try {
      setOrderPending(true);
      const response = await fetch('/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, quantity, price })
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error?.error || 'Order rejected');
      }
      await bootstrap();
      await fetchHistory(symbol);
    } catch (error) {
      console.error('Failed to place paper order', error);
      window.alert(error.message || 'Failed to place order');
    } finally {
      setOrderPending(false);
    }
  }, [active, bootstrap, fetchHistory]);

  useEffect(() => {
    if (!active) return;
    fetchAssets().catch((error) => console.error('Failed to refresh assets', error));
  }, [active, fetchAssets]);

  return (
    <div className="paper-dashboard">
      <HeaderBar portfolio={portfolio} timestamp={lastUpdate} />
      <main className="dashboard-grid">
        <div className="dashboard-grid__main">
          <ChartPanel
            history={history}
            assets={assets}
            analytics={selectedAnalytics}
            selectedSymbol={selectedSymbol}
            onSymbolChange={setSelectedSymbol}
          />
          <TradeControls assets={assets} onSubmit={handleManualOrder} loading={orderPending} />
        </div>
        <aside className="dashboard-grid__side">
          <AnalyticsPanel analytics={analytics} strategyLog={strategyLog} />
        </aside>
        <div className="dashboard-grid__full">
          <PortfolioPanel portfolio={portfolio} />
        </div>
      </main>
    </div>
  );
};

export default PaperTradingDashboard;
