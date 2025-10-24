import React from 'react';

export default function OrderBlotter({ trades }) {
  return (
    <div className="card grid-span-6 blotter">
      <h2>Recent Trades</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ textAlign: 'left', color: '#9ca3af', fontSize: '0.85rem' }}>
            <th>Symbol</th>
            <th>Side</th>
            <th>Size</th>
            <th>Price</th>
            <th>Fee</th>
          </tr>
        </thead>
        <tbody>
          {trades.length === 0 && (
            <tr>
              <td colSpan={5} style={{ padding: '1rem', textAlign: 'center', color: '#6b7280' }}>
                No trades yet
              </td>
            </tr>
          )}
          {trades.map((trade, index) => (
            <tr key={`${trade.ts}-${index}`} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <td>{trade.symbol}</td>
              <td style={{ color: trade.side === 'buy' ? '#34d399' : '#f87171' }}>{trade.side.toUpperCase()}</td>
              <td>{trade.size.toFixed(4)}</td>
              <td>{trade.price.toFixed(2)}</td>
              <td>{trade.fee.toFixed(4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
