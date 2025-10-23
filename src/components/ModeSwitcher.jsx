import React from 'react';

const MODE_LABELS = {
  paper: 'Paper Trading',
  live: 'Live Trading'
};

const ModeSwitcher = ({ modes = [], currentMode, onChange, loading }) => (
  <div className="mode-switcher" role="tablist" aria-label="Trading mode selector">
    {modes.map((mode) => {
      const isActive = mode === currentMode;
      const label = MODE_LABELS[mode] || mode;
      return (
        <button
          key={mode}
          type="button"
          role="tab"
          className={`mode-switcher__button${isActive ? ' mode-switcher__button--active' : ''}`}
          onClick={() => onChange(mode)}
          disabled={loading}
          aria-selected={isActive}
        >
          <span>{label}</span>
          {loading && isActive && <span className="mode-switcher__loader" aria-hidden="true" />}
        </button>
      );
    })}
  </div>
);

export default ModeSwitcher;
