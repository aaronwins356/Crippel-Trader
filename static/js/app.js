import { sendChatCompletion, DEFAULT_BASE_URL, DEFAULT_MODEL } from './llm_client.js';

const configForm = document.getElementById('config-form');
const configErrorsEl = document.getElementById('config-errors');
const reloadButton = document.getElementById('config-reload');
const saveButton = document.getElementById('config-save');
const tradeTableBody = document.querySelector('#trade-table tbody');
const tradeStatusEl = document.getElementById('trade-log-status');
const symbolForm = document.getElementById('symbol-form');
const symbolInput = document.getElementById('symbol-input');
const symbolErrors = document.getElementById('symbol-errors');
const wsStatus = document.getElementById('ws-status');
const bidEl = document.getElementById('bid');
const askEl = document.getElementById('ask');
const lastTradeEl = document.getElementById('last-trade');
const volumeEl = document.getElementById('volume');
const chatWindow = document.getElementById('chat-window');
const chatInput = document.getElementById('chat-input');
const sendChatButton = document.getElementById('send-chat');
const clearChatButton = document.getElementById('clear-chat');
const previewArea = document.getElementById('assistant-preview');
const copyPreviewButton = document.getElementById('copy-preview');
const themeToggle = document.getElementById('theme-toggle');
const priceChart = document.getElementById('price-chart');

let configCache = null;
let pollTimer = null;
let chatHistory = [];
let websocket = null;
let ohlcSeries = [];
let knownPairsPromise = null;

const KNOWN_QUOTES = ['USDT', 'USDC', 'USD', 'EUR', 'GBP', 'BTC', 'ETH'];
const BASE_REMAP = { BTC: 'XBT', XBT: 'XBT' };
const TRADE_LOG_PATH = 'logs/trades.jsonl';

function toggleTheme() {
  const isDark = document.body.classList.toggle('dark');
  localStorage.setItem('croc-theme', isDark ? 'dark' : 'light');
}

function initTheme() {
  const stored = localStorage.getItem('croc-theme');
  if (stored === 'dark') {
    document.body.classList.add('dark');
  }
}

function escapeHtml(value) {
  return value.replace(/[&<>]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[char]));
}

function formatMessage(content) {
  const escaped = escapeHtml(content);
  return escaped
    .replace(/```(\w+)?\n([\s\S]*?)```/g, (_, __, code) => `<pre><code>${code.trim()}</code></pre>`)
    .replace(/\n/g, '<br />');
}

function appendChat(role, content) {
  const entry = document.createElement('div');
  entry.className = `chat-entry ${role}`;
  entry.innerHTML = formatMessage(content);
  chatWindow.appendChild(entry);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function normaliseSymbolInput(input) {
  const raw = (input || '').toUpperCase().replace(/[^A-Z0-9/]/g, '/');
  const trimmed = raw.replace(/\/+/, '/').trim();
  if (trimmed.includes('/')) {
    const [baseRaw, quoteRaw] = trimmed.split('/').map((part) => part.trim());
    const base = BASE_REMAP[baseRaw] || baseRaw;
    const quote = quoteRaw || 'USD';
    return `${base}/${quote}`;
  }

  const compact = trimmed.replace(/\//g, '');
  for (const quote of KNOWN_QUOTES) {
    if (compact.endsWith(quote) && compact.length > quote.length) {
      const baseRaw = compact.slice(0, compact.length - quote.length);
      const base = BASE_REMAP[baseRaw] || baseRaw;
      return `${base}/${quote}`;
    }
  }

  if (compact.length >= 6) {
    const base = compact.slice(0, compact.length - 3);
    const quote = compact.slice(-3);
    return `${BASE_REMAP[base] || base}/${quote}`;
  }

  return compact;
}

async function fetchKrakenPairs() {
  if (!knownPairsPromise) {
    knownPairsPromise = (async () => {
      try {
        const response = await fetch('https://api.kraken.com/0/public/AssetPairs');
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const payload = await response.json();
        const map = new Map();
        for (const details of Object.values(payload.result || {})) {
          if (!details || typeof details !== 'object') continue;
          const wsName = details.wsname;
          if (typeof wsName !== 'string') continue;
          const normalized = normaliseSymbolInput(wsName);
          map.set(normalized, {
            ws: wsName,
            rest: wsName.replace('/', ''),
          });
        }
        if (map.size === 0) {
          throw new Error('Empty response');
        }
        return map;
      } catch (error) {
        console.warn('Falling back to static Kraken pair list:', error);
        return new Map([
          ['XBT/USD', { ws: 'XBT/USD', rest: 'XBTUSD' }],
          ['ETH/USD', { ws: 'ETH/USD', rest: 'ETHUSD' }],
          ['SOL/USD', { ws: 'SOL/USD', rest: 'SOLUSD' }],
          ['ADA/USD', { ws: 'ADA/USD', rest: 'ADAUSD' }],
        ]);
      }
    })();
  }
  return knownPairsPromise;
}

async function resolveSymbol(input) {
  const normalized = normaliseSymbolInput(input);
  const pairs = await fetchKrakenPairs();
  const match = pairs.get(normalized);
  if (!match) {
    throw new Error(`Unsupported Kraken pair: ${input}`);
  }
  return { ws: match.ws, rest: match.rest };
}

function populateForm(config) {
  document.getElementById('trading-mode').value = config.trading.mode;
  document.getElementById('initial-capital').value = config.trading.initial_capital;
  document.getElementById('aggression').value = config.trading.aggression;
  document.getElementById('symbols').value = config.trading.symbols.join(', ');
  document.getElementById('kraken-key').value = config.api.kraken_key;
  document.getElementById('kraken-secret').value = config.api.kraken_secret;
  document.getElementById('discord-webhook').value = config.api.discord_webhook;
  document.getElementById('llm-endpoint').value = config.llm.endpoint || DEFAULT_BASE_URL;
  document.getElementById('llm-model').value = config.llm.model || DEFAULT_MODEL;
  document.getElementById('llm-temperature').value = config.llm.temperature ?? 0.2;
  document.getElementById('maker-fee').value = config.fees.maker;
  document.getElementById('taker-fee').value = config.fees.taker;
  document.getElementById('log-level').value = config.runtime.log_level;
  document.getElementById('read-only').checked = Boolean(config.runtime.read_only_mode);
}

function parseFloatField(id) {
  const value = Number(document.getElementById(id).value);
  return Number.isFinite(value) ? value : NaN;
}

function getConfigFromForm() {
  const capital = parseFloatField('initial-capital');
  const makerFee = parseFloatField('maker-fee');
  const takerFee = parseFloatField('taker-fee');
  const temperatureValue = parseFloatField('llm-temperature');

  return {
    trading: {
      mode: document.getElementById('trading-mode').value,
      initial_capital: Number.isFinite(capital) ? capital : NaN,
      aggression: Number(document.getElementById('aggression').value),
      symbols: document
        .getElementById('symbols')
        .value.split(',')
        .map((symbol) => normaliseSymbolInput(symbol.trim()))
        .filter(Boolean),
    },
    api: {
      kraken_key: document.getElementById('kraken-key').value,
      kraken_secret: document.getElementById('kraken-secret').value,
      discord_webhook: document.getElementById('discord-webhook').value,
    },
    llm: {
      endpoint: document.getElementById('llm-endpoint').value || DEFAULT_BASE_URL,
      model: document.getElementById('llm-model').value || DEFAULT_MODEL,
      temperature: Number.isFinite(temperatureValue) ? temperatureValue : 0.2,
    },
    fees: {
      maker: Number.isFinite(makerFee) ? makerFee : NaN,
      taker: Number.isFinite(takerFee) ? takerFee : NaN,
    },
    runtime: {
      log_level: document.getElementById('log-level').value || 'INFO',
      read_only_mode: document.getElementById('read-only').checked,
    },
  };
}

function validateConfig(config) {
  const errors = [];
  if (!['paper', 'live'].includes(config.trading.mode)) {
    errors.push('Trading mode must be paper or live.');
  }
  if (!(config.trading.initial_capital > 0)) {
    errors.push('Initial capital must be positive.');
  }
  if (!(config.trading.aggression >= 1 && config.trading.aggression <= 10)) {
    errors.push('Aggression must be between 1 and 10.');
  }
  if (config.trading.symbols.length === 0) {
    errors.push('Provide at least one trading symbol.');
  }
  for (const [key, value] of Object.entries(config.fees)) {
    if (!(value >= 0 && value <= 0.1)) {
      errors.push(`${key} fee must be between 0 and 0.1.`);
    }
  }
  if (!(config.llm.temperature >= 0 && config.llm.temperature <= 1)) {
    errors.push('Temperature must be between 0 and 1.');
  }
  return errors;
}

function downloadConfig(updatedConfig) {
  const blob = new Blob([`${JSON.stringify(updatedConfig, null, 2)}\n`], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'config.json';
  link.click();
  URL.revokeObjectURL(url);
}

async function handleSave() {
  try {
    const updated = getConfigFromForm();
    const errors = validateConfig(updated);
    if (errors.length > 0) {
      configErrorsEl.textContent = errors.join('\n');
      return;
    }
    configErrorsEl.textContent = '';
    configCache = updated;
    downloadConfig(updated);
    configErrorsEl.textContent = 'Updated configuration downloaded as config.json.';
  } catch (error) {
    configErrorsEl.textContent = error.message;
  }
}

async function loadConfig() {
  configErrorsEl.textContent = 'Loading configuration…';
  try {
    const response = await fetch('config.json', { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`Failed to read config.json (${response.status})`);
    }
    const data = await response.json();
    configCache = data;
    populateForm(data);
    configErrorsEl.textContent = '';
    if (data.trading.symbols?.length) {
      symbolInput.value = data.trading.symbols[0];
      connectToKraken(data.trading.symbols[0]);
    }
  } catch (error) {
    configErrorsEl.textContent = error.message;
  }
}

function renderTradeRow(trade) {
  const row = document.createElement('tr');
  const capital = typeof trade.capital_used === 'number' ? trade.capital_used.toFixed(2) : trade.capital_used || '—';
  const stopLoss = typeof trade.stop_loss === 'number' ? trade.stop_loss.toFixed(2) : trade.stop_loss || '—';
  const fee = typeof trade.fee === 'number' ? trade.fee.toFixed(8) : trade.fee || '—';
  row.innerHTML = `
    <td>${new Date(trade.timestamp).toLocaleString()}</td>
    <td>${trade.symbol}</td>
    <td>${trade.side.toUpperCase()}</td>
    <td>${trade.size}</td>
    <td>${trade.price}</td>
    <td>${capital}</td>
    <td>${stopLoss}</td>
    <td>${trade.mode}</td>
    <td>${fee}</td>
  `;
  return row;
}

async function pollTrades() {
  try {
    const response = await fetch(`${TRADE_LOG_PATH}?_=${Date.now()}`, { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const text = await response.text();
    if (!text.trim()) {
      tradeTableBody.innerHTML = '';
      tradeStatusEl.textContent = 'No trades yet';
      return;
    }
    const entries = text
      .trim()
      .split(/\n+/)
      .map((line) => {
        try {
          return JSON.parse(line);
        } catch (error) {
          return null;
        }
      })
      .filter(Boolean)
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    tradeTableBody.innerHTML = '';
    entries.slice(0, 200).forEach((entry) => {
      tradeTableBody.appendChild(renderTradeRow(entry));
    });

    tradeStatusEl.textContent = `Updated ${new Date().toLocaleTimeString()} (${entries.length} trades)`;
  } catch (error) {
    tradeStatusEl.textContent = `Error loading trade log: ${error.message}`;
  } finally {
    pollTimer = window.setTimeout(pollTrades, 5000);
  }
}

function drawChart() {
  const ctx = priceChart.getContext('2d');
  const width = priceChart.width;
  const height = priceChart.height;
  ctx.clearRect(0, 0, width, height);
  if (ohlcSeries.length < 2) {
    return;
  }

  const closes = ohlcSeries.map((item) => item.close);
  const minPrice = Math.min(...closes);
  const maxPrice = Math.max(...closes);
  const range = maxPrice - minPrice || 1;

  ctx.beginPath();
  ohlcSeries.forEach((item, index) => {
    const x = (index / (ohlcSeries.length - 1)) * width;
    const y = height - ((item.close - minPrice) / range) * height;
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = '#0a84ff';
  ctx.lineWidth = 2;
  ctx.stroke();
}

function handleWebSocketMessage(event) {
  try {
    const data = JSON.parse(event.data);
    if (!Array.isArray(data)) {
      if (data.event === 'subscriptionStatus' && data.status === 'error') {
        symbolErrors.textContent = data.errorMessage || 'Subscription error';
        wsStatus.textContent = 'Error';
      }
      return;
    }

    const channel = data[2] || data[3];
    if (channel?.startsWith('ohlc')) {
      const candle = data[1];
      const close = Number(candle[4]);
      const timestamp = Number(candle[0]) * 1000;
      if (!Number.isFinite(close)) return;
      ohlcSeries.push({ timestamp, close });
      if (ohlcSeries.length > 400) {
        ohlcSeries = ohlcSeries.slice(-400);
      }
      drawChart();
    } else if (channel === 'trade') {
      const trade = data[1]?.[0];
      if (trade) {
        const [price, , time] = trade;
        lastTradeEl.textContent = `${Number(price).toFixed(2)} @ ${new Date(Number(time) * 1000).toLocaleTimeString()}`;
      }
    } else if (!channel && data[1]?.a) {
      const ticker = data[1];
      if (ticker.b?.[0]) {
        bidEl.textContent = Number(ticker.b[0]).toFixed(2);
      }
      if (ticker.a?.[0]) {
        askEl.textContent = Number(ticker.a[0]).toFixed(2);
      }
      if (ticker.v?.[1]) {
        volumeEl.textContent = Number(ticker.v[1]).toFixed(2);
      }
    }
  } catch (error) {
    console.warn('WebSocket parse error', error);
  }
}

function connectToKraken(symbol) {
  resolveSymbol(symbol)
    .then(({ ws }) => {
      symbolErrors.textContent = '';
      if (websocket) {
        websocket.close();
      }
      ohlcSeries = [];
      drawChart();
      wsStatus.textContent = `Connecting to ${ws}…`;
      websocket = new WebSocket('wss://ws.kraken.com');
      websocket.addEventListener('open', () => {
        wsStatus.textContent = `Connected to ${ws}`;
        const subscriptions = [
          { name: 'ohlc', interval: 1 },
          { name: 'ticker' },
          { name: 'trade' },
        ];
        subscriptions.forEach((subscription) => {
          websocket.send(
            JSON.stringify({
              event: 'subscribe',
              pair: [ws],
              subscription,
            }),
          );
        });
      });
      websocket.addEventListener('message', handleWebSocketMessage);
      websocket.addEventListener('close', () => {
        wsStatus.textContent = 'Disconnected';
      });
      websocket.addEventListener('error', () => {
        wsStatus.textContent = 'Connection error';
      });
    })
    .catch((error) => {
      symbolErrors.textContent = error.message;
      wsStatus.textContent = 'Disconnected';
    });
}

async function sendChat() {
  const message = chatInput.value.trim();
  if (!message) return;

  appendChat('user', message);
  chatHistory.push({ role: 'user', content: message });
  chatInput.value = '';

  const baseUrl = configCache?.llm?.endpoint || DEFAULT_BASE_URL;
  const model = configCache?.llm?.model || DEFAULT_MODEL;
  const temperature = configCache?.llm?.temperature ?? 0.2;

  try {
    const trimmedHistory = chatHistory.slice(-20); // keep context manageable
    const response = await sendChatCompletion({
      baseUrl,
      model,
      messages: trimmedHistory,
      temperature,
    });
    chatHistory.push({ role: 'assistant', content: response });
    appendChat('assistant', response);
    previewArea.value = response;
  } catch (error) {
    appendChat('assistant', `Error: ${error.message}`);
  }
}

function clearChat() {
  chatHistory = [];
  chatWindow.innerHTML = '';
  previewArea.value = '';
}

async function copyPreview() {
  try {
    if (!previewArea.value) {
      return;
    }
    await navigator.clipboard.writeText(previewArea.value);
    copyPreviewButton.textContent = 'Copied!';
    setTimeout(() => {
      copyPreviewButton.textContent = 'Copy preview';
    }, 1500);
  } catch (error) {
    copyPreviewButton.textContent = 'Copy failed';
    console.warn('Clipboard error', error);
  }
}

function handleSymbolSubmit(event) {
  event.preventDefault();
  const symbol = symbolInput.value.trim();
  if (!symbol) {
    symbolErrors.textContent = 'Provide a symbol (e.g. BTC/USD).';
    return;
  }
  connectToKraken(symbol);
}

function attachEvents() {
  reloadButton.addEventListener('click', loadConfig);
  saveButton.addEventListener('click', handleSave);
  configForm.addEventListener('input', () => {
    configErrorsEl.textContent = '';
  });
  symbolForm.addEventListener('submit', handleSymbolSubmit);
  sendChatButton.addEventListener('click', sendChat);
  chatInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
      sendChat();
    }
  });
  clearChatButton.addEventListener('click', clearChat);
  copyPreviewButton.addEventListener('click', copyPreview);
  themeToggle.addEventListener('click', toggleTheme);
}

function init() {
  initTheme();
  attachEvents();
  loadConfig();
  pollTrades();
}

init();
