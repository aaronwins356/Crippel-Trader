import React, { useCallback, useEffect, useState } from 'react';
import ModeSwitcher from './components/ModeSwitcher.jsx';
import PaperTradingDashboard from './components/PaperTradingDashboard.jsx';
import LiveTradingDashboard from './components/LiveTradingDashboard.jsx';
import useTradingStream from './hooks/useTradingStream.js';

const App = () => {
  const [mode, setMode] = useState('paper');
  const [availableModes, setAvailableModes] = useState(['paper', 'live']);
  const [modeLoading, setModeLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadModes = useCallback(async () => {
    try {
      setModeLoading(true);
      const response = await fetch('/api/modes');
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || 'Failed to load trading modes');
      }
      setMode(data.current || 'paper');
      setAvailableModes(data.available || ['paper', 'live']);
      setError(null);
    } catch (err) {
      console.error('Failed to load trading modes', err);
      setError(err.message || 'Failed to load trading modes');
    } finally {
      setModeLoading(false);
    }
  }, []);

  useEffect(() => {
    loadModes();
  }, [loadModes]);

  const handleModeChange = useCallback(async (nextMode) => {
    if (!nextMode || nextMode === mode) {
      return;
    }
    try {
      setModeLoading(true);
      const response = await fetch('/api/modes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: nextMode })
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.error || 'Failed to switch trading mode');
      }
      setMode(payload.mode || nextMode);
      setError(null);
    } catch (err) {
      console.error('Failed to switch trading mode', err);
      setError(err.message || 'Failed to switch trading mode');
    } finally {
      setModeLoading(false);
    }
  }, [mode]);

  useTradingStream(
    useCallback((payload) => {
      if (payload?.type === 'mode:change' && payload.mode) {
        setMode(payload.mode);
      }
    }, []),
    { enabled: true }
  );

  return (
    <div className="app-shell">
      <div className="mode-toolbar">
        <ModeSwitcher
          modes={availableModes}
          currentMode={mode}
          onChange={handleModeChange}
          loading={modeLoading}
        />
        {error && <span className="mode-toolbar__error">{error}</span>}
      </div>
      {mode === 'live' ? (
        <LiveTradingDashboard active={!modeLoading && mode === 'live'} />
      ) : (
        <PaperTradingDashboard active={!modeLoading && mode === 'paper'} />
      )}
    </div>
  );
};

export default App;
