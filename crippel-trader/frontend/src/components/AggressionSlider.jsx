import React from 'react';

export default function AggressionSlider({ value, onChange }) {
  return (
    <div className="card grid-span-4">
      <h2>Aggression</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <input
          className="slider"
          type="range"
          min="1"
          max="10"
          step="1"
          value={value}
          onChange={(event) => onChange(Number(event.target.value))}
        />
        <span>Level {value} / 10</span>
        <small>
          Higher aggression increases position size, reduces stop distance, and lowers signal
          thresholds. Adjust cautiously.
        </small>
      </div>
    </div>
  );
}
