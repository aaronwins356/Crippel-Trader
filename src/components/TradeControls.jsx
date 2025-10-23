import React, { useEffect, useMemo, useState } from 'react';

const TradeControls = ({ assets = [], onSubmit, loading }) => {
  const [symbol, setSymbol] = useState(assets[0]?.symbol || 'BTC-USD');
  const [side, setSide] = useState('buy');
  const [size, setSize] = useState(1);
  const [priceOverride, setPriceOverride] = useState('');

  const sizeLabel = useMemo(() => (side === 'buy' ? 'Buy Size' : 'Sell Size'), [side]);

  useEffect(() => {
    if (!assets.length) return;
    if (!assets.find((asset) => asset.symbol === symbol)) {
      setSymbol(assets[0].symbol);
    }
  }, [assets, symbol]);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!symbol || Number(size) <= 0 || typeof onSubmit !== 'function') return;
    const quantity = side === 'buy' ? Math.abs(Number(size)) : -Math.abs(Number(size));
    const price = priceOverride ? Number(priceOverride) : undefined;
    const confirmation = window.confirm(`Confirm ${side.toUpperCase()} ${Math.abs(quantity)} ${symbol}?`);
    if (!confirmation) return;
    onSubmit({ symbol, quantity, price });
  };

  return (
    <section className="panel trade-panel">
      <header className="panel__header">
        <div>
          <h2>Manual Execution</h2>
          <span className="panel__subtitle">Override automation and route discretionary orders</span>
        </div>
      </header>
      <div className="panel__body">
        <form className="trade-form" onSubmit={handleSubmit}>
          <label>
            <span>Symbol</span>
            <select value={symbol} onChange={(event) => setSymbol(event.target.value)}>
              {(assets || []).map((asset) => (
                <option key={asset.symbol} value={asset.symbol}>
                  {asset.symbol} — {asset.name}
                </option>
              ))}
            </select>
          </label>
          <div className="trade-form__sides">
            <button type="button" className={side === 'buy' ? 'active' : ''} onClick={() => setSide('buy')}>
              Buy
            </button>
            <button type="button" className={side === 'sell' ? 'active' : ''} onClick={() => setSide('sell')}>
              Sell
            </button>
          </div>
          <label>
            <span>{sizeLabel}</span>
            <input type="number" min="0" step="1" value={size} onChange={(event) => setSize(event.target.value)} />
          </label>
          <label>
            <span>Limit Price (optional)</span>
            <input
              type="number"
              min="0"
              step="0.01"
              value={priceOverride}
              onChange={(event) => setPriceOverride(event.target.value)}
              placeholder="Market"
            />
          </label>
          <button type="submit" disabled={loading}>
            {loading ? 'Routing…' : `${side === 'buy' ? 'Send Buy' : 'Send Sell'} Order`}
          </button>
        </form>
      </div>
    </section>
  );
};

export default TradeControls;
