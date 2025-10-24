import React from 'react';

export default function ModeToggle({ mode, onToggle }) {
  const isLive = mode === 'live';
  return (
    <div className="card grid-span-4">
      <h2>Mode</h2>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div className={isLive ? 'badge-live' : 'badge-paper'}>
          {isLive ? 'LIVE' : 'PAPER'}
        </div>
        <button
          onClick={onToggle}
          style={{
            padding: '0.75rem 1.5rem',
            background: isLive ? '#f87171' : '#34d399',
            color: '#0b1015',
            border: 'none',
            borderRadius: '9999px',
            cursor: 'pointer',
            fontWeight: '600'
          }}
        >
          Switch to {isLive ? 'Paper' : 'Live'}
        </button>
      </div>
      {isLive && (
        <p className="warning">LIVE MODE — Orders will route to real exchanges. Confirm twice!</p>
      )}
    </div>
  );
}
