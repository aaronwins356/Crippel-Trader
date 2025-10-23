import EventEmitter from 'events';

export default class TradingModeService extends EventEmitter {
  constructor({ marketDataService, liveTradingService, defaultMode = 'paper' } = {}) {
    super();
    this.marketDataService = marketDataService;
    this.liveTradingService = liveTradingService;
    this.availableModes = ['paper', 'live'];
    this.currentMode = this.availableModes.includes(defaultMode) ? defaultMode : 'paper';
  }

  getMode() {
    return this.currentMode;
  }

  getAvailableModes() {
    return [...this.availableModes];
  }

  isPaperMode() {
    return this.currentMode === 'paper';
  }

  isLiveMode() {
    return this.currentMode === 'live';
  }

  setMode(mode) {
    if (!this.availableModes.includes(mode)) {
      throw new Error(`Unknown mode: ${mode}`);
    }
    if (mode === this.currentMode) {
      return this.currentMode;
    }
    this.currentMode = mode;
    this.emit('mode:change', { type: 'mode:change', mode });
    return this.currentMode;
  }

  getPaperService() {
    return this.marketDataService;
  }

  getLiveService() {
    return this.liveTradingService;
  }
}
