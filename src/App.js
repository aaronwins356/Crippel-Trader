import React, { useCallback, useEffect, useMemo, useState } from 'react';
import dayjs from 'dayjs';
import HeaderBar from './components/HeaderBar.jsx';
import ChartPanel from './components/ChartPanel.jsx';
import PortfolioPanel from './components/PortfolioPanel.jsx';
import AnalyticsPanel from './components/AnalyticsPanel.jsx';
import TradeControls from './components/TradeControls.jsx';
import useTradingStream from './hooks/useTradingStream.js';

const DEFAULT_HISTORY_LENGTH = 240;

const normaliseHistory = (candles) => candles.map((item) => ({
  ...item,
  time: dayjs(item.timestamp).format('HH:mm')
}));

const App = () => {
  const [assets, setAssets] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [portfolio, setPortfolio] = useState(null);
  const [strategyLog, setStrategyLog] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState('BTC-USD');
  const [history, setHistory] = useState([]);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [orderPending, setOrderPending] = useState(false);

  const fetchAssets = useCallback(async () => {
    const response = await fetch('/api/assets');
    const data = await response.json();
    setAssets(data.assets || []);
    if (data.assets?.length && !data.assets.find((asset) => asset.symbol === selectedSymbol)) {
      setSelectedSymbol(data.assets[0].symbol);
    }
  }, [selectedSymbol]);

  const fetchHistory = useCallback(async (symbol) => {
    const response = await fetch(`/api/history/${symbol}`);
    const data = await response.json();
    setHistory(normaliseHistory((data?.candles || []).slice(-DEFAULT_HISTORY_LENGTH)));
  }, []);

  const bootstrap = useCallback(async () => {
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
  }, [selectedSymbol]);

  useEffect(() => {
    bootstrap().catch((error) => console.error('Failed to bootstrap state', error));
  }, [bootstrap]);

  useEffect(() => {
    fetchHistory(selectedSymbol).catch((error) => console.error('Failed to load history', error));
  }, [selectedSymbol, fetchHistory]);

  const handleStreamPayload = useCallback((payload) => {
    if (!payload || payload.type !== 'market:update') return;
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
  }, [selectedSymbol]);

  useTradingStream(handleStreamPayload);

  const selectedAnalytics = useMemo(() => (
    analytics?.assets?.find((asset) => asset.symbol === selectedSymbol) || null
  ), [analytics, selectedSymbol]);

  const handleManualOrder = useCallback(async ({ symbol, quantity, price }) => {
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
      console.error('Failed to place order', error);
      window.alert(error.message || 'Failed to place order');
    } finally {
      setOrderPending(false);
    }
  }, [bootstrap, fetchHistory]);

  useEffect(() => {
    fetchAssets().catch((error) => console.error('Failed to refresh assets', error));
  }, [fetchAssets]);

  return (
    <div className="app-shell">
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

export default App;
