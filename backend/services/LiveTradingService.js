import EventEmitter from 'events';
import { randomUUID } from 'crypto';
import dayjs from 'dayjs';
import KrakenClient from './integrations/KrakenClient.js';
import { normalizeNumber } from '../utils/indicators.js';
import { logger } from '../utils/logger.js';

const DEFAULT_INTERVAL_MS = 5000;
const DEFAULT_CAPITAL = 100000;

const SYMBOL_POOL = [
  'BTC/USD',
  'ETH/USD',
  'SOL/USD',
  'MATIC/USD',
  'ATOM/USD',
  'DOGE/USD'
];

const WORKER_PROFILES = [
  { id: 'worker-alpha', name: 'Alpha Worker', focus: 'High-frequency momentum' },
  { id: 'worker-beta', name: 'Beta Worker', focus: 'Mean reversion scalps' },
  { id: 'worker-gamma', name: 'Gamma Worker', focus: 'Liquidity sweeps' },
  { id: 'worker-delta', name: 'Delta Worker', focus: 'Funding arbitrage' }
];

const randomBetween = (min, max) => Math.random() * (max - min) + min;

export default class LiveTradingService extends EventEmitter {
  constructor({ intervalMs = DEFAULT_INTERVAL_MS, capital = DEFAULT_CAPITAL } = {}) {
    super();
    this.intervalMs = intervalMs;
    this.initialCapital = capital;
    this.cash = capital;
    this.realizedPnL = 0;
    this.positionBook = new Map();
    this.trades = [];
    this.plHistory = [];
    this.researchNotes = [];

    this.brain = {
      name: 'Brain Bot',
      status: 'initializing',
      directives: [
        'Stabilize exposure across worker cohorts',
        'Favor high Sharpe strategies under 2% slippage tolerance'
      ],
      researchFocus: 'Watching macro liquidity shifts'
    };

    this.workers = WORKER_PROFILES.map((worker) => ({
      ...worker,
      status: 'warming',
      confidence: 0,
      lastSignal: null,
      pendingTasks: 0
    }));

    this.executor = {
      status: 'idle',
      lastDecision: null,
      lastOrderReference: null,
      mode: 'simulation'
    };

    this.krakenClient = new KrakenClient({});
    if (this.krakenClient.enabled) {
      this.executor.mode = 'live';
    }

    this.interval = setInterval(() => {
      this.tick().catch((error) => {
        logger.error('Live trading tick failed', error);
      });
    }, this.intervalMs);

    this.tick().catch((error) => {
      logger.error('Initial live trading tick failed', error);
    });
  }

  async tick() {
    this.updateBrainState();
    this.generateResearchInsight();

    await Promise.all(
      this.workers.map(async (worker) => {
        this.updateWorkerState(worker);
        if (Math.random() < 0.35) {
          await this.generateWorkerTrade(worker);
        }
      })
    );

    this.captureSnapshot();
    this.emitUpdate();
  }

  updateBrainState() {
    const activeSignals = this.trades.slice(-5).map((trade) => `${trade.symbol} ${trade.side} ${trade.quantity}`);
    this.brain = {
      ...this.brain,
      status: activeSignals.length ? 'coordinating execution' : 'monitoring',
      activeSignals
    };
  }

  generateResearchInsight() {
    const researchAuthors = ['Quant Ops', 'Market Intelligence', 'Macro Desk', 'On-chain Insights'];
    const themes = [
      'funding spreads tightening across majors',
      'elevated perp open interest versus spot',
      'macro dollar weakness supporting risk assets',
      'volatility compression indicating breakout setup',
      'options skew rotating bullish on 1w tenors'
    ];
    const catalysts = [
      'Asian session liquidity window',
      'incoming CPI release',
      'Fed speakers in focus',
      'large on-chain transfer cluster',
      'derivatives expiry roll'
    ];

    const note = {
      id: randomUUID(),
      author: researchAuthors[Math.floor(Math.random() * researchAuthors.length)],
      theme: themes[Math.floor(Math.random() * themes.length)],
      catalyst: catalysts[Math.floor(Math.random() * catalysts.length)],
      timestamp: dayjs().toISOString()
    };
    this.researchNotes.unshift(note);
    if (this.researchNotes.length > 30) {
      this.researchNotes.length = 30;
    }
  }

  updateWorkerState(worker) {
    const phase = Math.random();
    if (phase > 0.75) {
      worker.status = 'deploying signal';
    } else if (phase > 0.4) {
      worker.status = 'scanning';
    } else {
      worker.status = 'refining';
    }
    worker.confidence = normalizeNumber(randomBetween(50, 99), 2);
    worker.pendingTasks = Math.floor(Math.random() * 3);
  }

  async generateWorkerTrade(worker) {
    const symbol = SYMBOL_POOL[Math.floor(Math.random() * SYMBOL_POOL.length)];
    const side = Math.random() > 0.5 ? 'buy' : 'sell';
    const quantity = normalizeNumber(randomBetween(0.5, 3.5), 3);
    const priceBase = side === 'buy' ? randomBetween(0.98, 1.02) : randomBetween(0.96, 1.04);
    const referencePrice = this.resolveReferencePrice(symbol);
    const price = normalizeNumber(referencePrice * priceBase, 2);
    const confidence = normalizeNumber(randomBetween(55, 92), 2);
    const narrative = side === 'buy'
      ? 'Worker expects continuation after liquidity sweep'
      : 'Worker sees exhaustion and looks to mean revert';

    worker.lastSignal = {
      symbol,
      side,
      price,
      quantity,
      confidence,
      timestamp: dayjs().toISOString(),
      narrative
    };

    await this.submitWorkerTrade({
      workerId: worker.id,
      workerName: worker.name,
      symbol,
      side,
      quantity,
      price,
      confidence,
      narrative
    });
  }

  resolveReferencePrice(symbol) {
    // Provide deterministic pseudo prices so charts look sensible.
    const base = {
      'BTC/USD': 68000,
      'ETH/USD': 3500,
      'SOL/USD': 150,
      'MATIC/USD': 0.95,
      'ATOM/USD': 12,
      'DOGE/USD': 0.15
    };
    return base[symbol] ?? 100;
  }

  async submitWorkerTrade(tradeRequest) {
    const {
      workerId,
      workerName,
      symbol,
      side,
      quantity,
      price,
      confidence,
      narrative
    } = tradeRequest;
    const numericQuantity = Number(quantity);
    const numericPrice = Number(price);
    if (!symbol || !side || !Number.isFinite(numericQuantity) || !Number.isFinite(numericPrice)) {
      throw new Error('Trade request missing required fields');
    }

    const requestId = randomUUID();
    this.executor.status = 'evaluating';
    this.executor.lastDecision = {
      requestId,
      workerId,
      workerName,
      symbol,
      side,
      quantity,
      price,
      confidence,
      narrative,
      timestamp: dayjs().toISOString()
    };

    try {
      const executionResult = await this.krakenClient.submitOrder({
        symbol,
        side,
        quantity: numericQuantity,
        price: numericPrice,
        meta: { requestId, workerId }
      });
      this.executor.lastOrderReference = executionResult.reference;
      const trade = await this.recordTrade({
        id: requestId,
        symbol,
        side,
        quantity: numericQuantity,
        price: numericPrice,
        confidence,
        workerId,
        workerName,
        narrative,
        execution: executionResult
      });
      this.executor.status = 'idle';
      this.emitUpdate();
      return trade;
    } catch (error) {
      logger.error('Failed to execute live trade', error);
      this.executor.status = 'error';
      this.executor.lastDecision.error = error.message;
      throw error;
    }
  }

  async recordTrade({ id, symbol, side, quantity, price, confidence, workerId, workerName, narrative, execution }) {
    const timestamp = dayjs().toISOString();
    const trade = {
      id,
      symbol,
      side,
      quantity,
      price,
      confidence,
      workerId,
      workerName,
      narrative,
      execution,
      timestamp
    };

    this.trades.unshift(trade);
    if (this.trades.length > 200) {
      this.trades.length = 200;
    }

    this.updatePositions({ symbol, side, quantity, price });
    this.captureSnapshot();
    return trade;
  }

  updatePositions({ symbol, side, quantity, price }) {
    const signedQuantity = side === 'buy' ? quantity : -quantity;
    const value = price * quantity;
    if (side === 'buy') {
      this.cash -= value;
    } else {
      this.cash += value;
    }

    const position = this.positionBook.get(symbol) || {
      symbol,
      quantity: 0,
      avgPrice: 0,
      lastPrice: price
    };

    const previousQuantity = position.quantity;
    const previousAverage = position.avgPrice;
    let realized = 0;

    if (previousQuantity === 0 || Math.sign(previousQuantity) === Math.sign(signedQuantity)) {
      const totalQuantity = Math.abs(previousQuantity) + Math.abs(signedQuantity);
      const weightedPrice = Math.abs(previousQuantity) * previousAverage + Math.abs(signedQuantity) * price;
      position.quantity = normalizeNumber(previousQuantity + signedQuantity, 6);
      position.avgPrice = position.quantity === 0 ? 0 : normalizeNumber(weightedPrice / totalQuantity, 6);
    } else {
      const closingQuantity = Math.min(Math.abs(previousQuantity), Math.abs(signedQuantity));
      realized = closingQuantity * (price - previousAverage) * Math.sign(previousQuantity);
      const residual = Math.abs(signedQuantity) - closingQuantity;

      if (Math.abs(previousQuantity) > Math.abs(signedQuantity)) {
        // Partially close existing position.
        const nextQuantity = previousQuantity + signedQuantity;
        position.quantity = Math.abs(nextQuantity) < 1e-8 ? 0 : normalizeNumber(nextQuantity, 6);
        position.avgPrice = position.quantity === 0 ? 0 : previousAverage;
      } else if (residual > 0) {
        // Closed and flipped into the opposite direction.
        const direction = Math.sign(signedQuantity);
        position.quantity = normalizeNumber(direction * residual, 6);
        position.avgPrice = normalizeNumber(price, 6);
      } else {
        position.quantity = 0;
        position.avgPrice = 0;
      }
    }

    position.lastPrice = price;
    if (Math.abs(position.quantity) < 1e-8) {
      this.positionBook.delete(symbol);
    } else {
      this.positionBook.set(symbol, position);
    }

    this.realizedPnL += realized;
  }

  captureSnapshot() {
    const timestamp = dayjs().toISOString();
    const openPositions = Array.from(this.positionBook.values()).map((position) => {
      const unrealized = (position.lastPrice - position.avgPrice) * position.quantity;
      return {
        symbol: position.symbol,
        quantity: normalizeNumber(position.quantity, 4),
        avgPrice: normalizeNumber(position.avgPrice, 4),
        lastPrice: normalizeNumber(position.lastPrice, 4),
        direction: position.quantity >= 0 ? 'long' : 'short',
        unrealizedPnl: normalizeNumber(unrealized, 2)
      };
    });

    const totalUnrealized = openPositions.reduce((acc, item) => acc + item.unrealizedPnl, 0);
    const equity = this.cash + openPositions.reduce((acc, item) => acc + item.lastPrice * item.quantity, 0);

    this.plHistory.push({
      timestamp,
      equity: normalizeNumber(equity, 2),
      realized: normalizeNumber(this.realizedPnL, 2),
      unrealized: normalizeNumber(totalUnrealized, 2)
    });
    if (this.plHistory.length > 720) {
      this.plHistory.shift();
    }

    this.snapshot = {
      timestamp,
      openPositions,
      equity,
      cash: this.cash,
      realizedPnL: this.realizedPnL,
      unrealizedPnL: totalUnrealized
    };
  }

  emitUpdate() {
    this.emit('update', {
      type: 'live:update',
      state: this.getState()
    });
  }

  getState() {
    return {
      timestamp: dayjs().toISOString(),
      brain: this.brain,
      research: this.researchNotes,
      workers: this.workers,
      executor: this.executor,
      trades: this.trades,
      openPositions: this.snapshot?.openPositions ?? [],
      performance: this.plHistory,
      capital: {
        initial: this.initialCapital,
        cash: normalizeNumber(this.cash, 2),
        realizedPnL: normalizeNumber(this.realizedPnL, 2),
        unrealizedPnL: normalizeNumber(this.snapshot?.unrealizedPnL ?? 0, 2),
        equity: normalizeNumber(this.snapshot?.equity ?? this.initialCapital, 2)
      }
    };
  }

  addResearchInsight({ author, theme, catalyst, timestamp = dayjs().toISOString() }) {
    const note = {
      id: randomUUID(),
      author: author || 'Research Desk',
      theme: theme || 'General market observation',
      catalyst: catalyst || 'Operator supplied',
      timestamp
    };
    this.researchNotes.unshift(note);
    if (this.researchNotes.length > 30) {
      this.researchNotes.length = 30;
    }
    this.emitUpdate();
    return note;
  }

  shutdown() {
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
    this.removeAllListeners();
    logger.info('Live trading service stopped');
  }
}
