import React from 'react';

export default function ConnectionIndicator({ status }) {
  const stateClass = status === 'connected' ? 'online' : status === 'connecting' ? '' : 'offline';
  const label = status === 'connected' ? 'Connected' : status === 'connecting' ? 'Connecting…' : 'Disconnected';
  return (
    <div className={`card connection-indicator grid-span-4 ${stateClass}`}>
      <span />
      <div>
        <h2>Data Feed</h2>
        <div>{label}</div>
      </div>
    </div>
  );
}
