const stateSocket = new WebSocket(`${location.origin.replace('http', 'ws')}/ws/state`);
const chatWindow = document.getElementById('chat-window');
const chatInput = document.getElementById('chat-input');
const sendChatBtn = document.getElementById('send-chat');
const previewDiffBtn = document.getElementById('preview-diff');
const diffOutput = document.getElementById('diff-output');
const configErrorsEl = document.getElementById('config-errors');
const configForm = document.getElementById('config-form');
const themeToggle = document.getElementById('theme-toggle');
const exportZipBtn = document.getElementById('export-zip');
const pairSelector = document.getElementById('pair-selector');
const priceChart = document.getElementById('price-chart');
const bidEl = document.getElementById('bid');
const askEl = document.getElementById('ask');
const lastTradeEl = document.getElementById('last-trade');
const wsStatus = document.getElementById('ws-status');
const tradeLog = document.getElementById('trade-log');
const tradeErrors = document.getElementById('trade-errors');
const positionsBody = document.querySelector('#positions-table tbody');
const ordersBody = document.querySelector('#orders-table tbody');
const balanceEl = document.getElementById('balance');
const pnlEl = document.getElementById('pnl');
const feesEl = document.getElementById('fees');
const executeTradeBtn = document.getElementById('execute-trade');
const tradeSymbol = document.getElementById('trade-symbol');
const tradeSide = document.getElementById('trade-side');
const tradeSize = document.getElementById('trade-size');
const tradePrice = document.getElementById('trade-price');

let configCache = null;
let lastChatResponse = '';
let candleSeries = [];
let priceWs = null;
let chartCtx = priceChart.getContext('2d');

function renderState(payload) {
  if (payload.errors) {
    configErrorsEl.textContent = payload.errors.map((e) => `${e.field}: ${e.message}`).join('\n');
    return;
  }
  const state = payload.state;
  if (!state) return;
  configErrorsEl.textContent = '';
  balanceEl.textContent = state.balance.toFixed(2);
  pnlEl.textContent = state.daily_realized_pnl.toFixed(2);
  feesEl.textContent = state.total_fees_paid.toFixed(2);

  positionsBody.innerHTML = '';
  state.positions.forEach((pos) => {
    const row = document.createElement('tr');
    row.innerHTML = `<td>${pos.symbol}</td><td>${pos.size}</td><td>${pos.avg_price}</td><td>${pos.unrealized_pnl}</td>`;
    positionsBody.appendChild(row);
  });

  ordersBody.innerHTML = '';
  state.open_orders.forEach((order) => {
    const row = document.createElement('tr');
    row.innerHTML = `<td>${order.id || '-'} </td><td>${order.symbol}</td><td>${order.side}</td><td>${order.size}</td><td>${order.price}</td>`;
    ordersBody.appendChild(row);
  });

  tradeLog.innerHTML = '';
  state.trades.forEach((trade) => {
    const li = document.createElement('li');
    li.textContent = `${trade.timestamp} :: ${trade.side.toUpperCase()} ${trade.size} ${trade.symbol} @ ${trade.price} (fee: ${trade.fee})`;
    tradeLog.appendChild(li);
  });
}

stateSocket.addEventListener('message', (event) => {
  const payload = JSON.parse(event.data);
  renderState(payload);
});

stateSocket.addEventListener('close', () => {
  configErrorsEl.textContent = 'Lost connection to backend.';
});

async function loadConfig() {
  try {
    const response = await fetch('/config');
    const data = await response.json();
    if (!response.ok) {
      configErrorsEl.textContent = data.errors ? data.errors.map((e) => `${e.field}: ${e.message}`).join('\n') : 'Configuration error';
      return;
    }
    configCache = data.config;
    populateForm(configCache);
    setupPairSelector(configCache.trading.pairs);
    connectPriceFeed(pairSelector.value || configCache.trading.pairs[0]);
  } catch (err) {
    configErrorsEl.textContent = `Failed to load config: ${err.message}`;
  }
}

function populateForm(config) {
  document.getElementById('trading-mode').value = config.trading.mode;
  document.getElementById('capital').value = config.trading.capital;
  document.getElementById('aggression').value = config.trading.aggression;
  document.getElementById('maker-fee').value = config.fees.maker;
  document.getElementById('taker-fee').value = config.fees.taker;
  document.getElementById('tickers').value = config.trading.pairs.join(',');
  document.getElementById('llm-endpoint').value = config.llm.endpoint;
  document.getElementById('llm-model').value = config.llm.model;
  document.getElementById('llm-temperature').value = config.llm.temperature;
  document.getElementById('llm-max-tokens').value = config.llm.max_tokens;
  document.getElementById('refresh-interval').value = config.runtime.refresh_interval;
  document.getElementById('read-only').checked = config.runtime.read_only;
}

configForm.addEventListener('submit', (event) => {
  event.preventDefault();
  if (!configCache) return;
  const formData = new FormData(configForm);
  const preview = Object.fromEntries(formData.entries());
  preview['read-only'] = document.getElementById('read-only').checked;
  diffOutput.textContent = JSON.stringify(preview, null, 2);
});

function appendChat(role, content) {
  const div = document.createElement('div');
  div.className = `chat-message ${role}`;
  div.innerHTML = `<strong>${role === 'user' ? 'You' : 'Assistant'}:</strong><br/>${highlightCode(content)}`;
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function highlightCode(text) {
  return text.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
    const escaped = code.replace(/[&<>]/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;'}[c]));
    return `<pre data-lang="${lang || ''}"><code>${escaped}</code></pre>`;
  });
}

async function sendChat() {
  const message = chatInput.value.trim();
  if (!message || !configCache) return;
  appendChat('user', message);
  chatInput.value = '';
  try {
    const payload = {
      model: configCache.llm.model,
      messages: [
        { role: 'system', content: 'You are a Python trading bot developer.' },
        { role: 'user', content: message }
      ],
      temperature: configCache.llm.temperature,
      max_tokens: configCache.llm.max_tokens
    };
    const response = await fetch(configCache.llm.endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    const assistantMessage = data.choices?.[0]?.message?.content || 'No response';
    lastChatResponse = assistantMessage;
    appendChat('assistant', assistantMessage);
  } catch (err) {
    appendChat('assistant', `Error: ${err.message}`);
  }
}

sendChatBtn.addEventListener('click', sendChat);
chatInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && event.ctrlKey) {
    sendChat();
  }
});

previewDiffBtn.addEventListener('click', () => {
  if (!lastChatResponse) {
    diffOutput.textContent = 'No assistant response to diff.';
    return;
  }
  diffOutput.textContent = lastChatResponse;
});

themeToggle.addEventListener('click', () => {
  document.body.classList.toggle('theme-dark');
});

exportZipBtn.addEventListener('click', async () => {
  try {
    const response = await fetch('/export');
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || 'Export archive not available');
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'croc-bot-export.zip';
    link.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert(err.message);
  }
});

function setupPairSelector(pairs) {
  pairSelector.innerHTML = '';
  pairs.forEach((pair) => {
    const option = document.createElement('option');
    option.value = pair;
    option.textContent = pair;
    pairSelector.appendChild(option);
  });
  pairSelector.addEventListener('change', () => {
    connectPriceFeed(pairSelector.value);
  });
}

function connectPriceFeed(pair) {
  if (priceWs) {
    priceWs.close();
  }
  wsStatus.textContent = 'Connecting…';
  candleSeries = [];
  chartCtx.clearRect(0, 0, priceChart.width, priceChart.height);
  priceWs = new WebSocket('wss://ws.kraken.com/');
  priceWs.addEventListener('open', () => {
    wsStatus.textContent = `Connected (${pair})`;
    priceWs.send(JSON.stringify({
      event: 'subscribe',
      pair: [pair],
      subscription: { name: 'ohlc', interval: 1 }
    }));
    priceWs.send(JSON.stringify({ event: 'subscribe', pair: [pair], subscription: { name: 'ticker' } }));
    priceWs.send(JSON.stringify({ event: 'subscribe', pair: [pair], subscription: { name: 'trade' } }));
  });
  priceWs.addEventListener('message', (evt) => handlePriceMessage(evt, pair));
  priceWs.addEventListener('close', () => {
    wsStatus.textContent = 'Disconnected';
  });
}

function handlePriceMessage(evt, pair) {
  const data = JSON.parse(evt.data);
  if (!Array.isArray(data)) {
    return;
  }
  const channelType = data[3];
  if (channelType?.startsWith('ohlc')) {
    const candle = data[1];
    const close = parseFloat(candle[4]);
    const timestamp = parseFloat(candle[0]);
    candleSeries.push({ timestamp, close });
    if (candleSeries.length > 200) candleSeries.shift();
    drawChart();
  } else if (channelType === 'trade') {
    const last = data[1][0];
    lastTradeEl.textContent = `Last: ${parseFloat(last[0]).toFixed(2)} @ ${new Date(parseFloat(last[2]) * 1000).toLocaleTimeString()}`;
  } else if (!channelType && data[1]?.a && data[1]?.b && data[2] === pair) {
    bidEl.textContent = `Bid: ${parseFloat(data[1].b[0]).toFixed(2)}`;
    askEl.textContent = `Ask: ${parseFloat(data[1].a[0]).toFixed(2)}`;
  }
}

function drawChart() {
  const width = priceChart.width;
  const height = priceChart.height;
  chartCtx.clearRect(0, 0, width, height);
  if (candleSeries.length < 2) return;
  const minPrice = Math.min(...candleSeries.map((c) => c.close));
  const maxPrice = Math.max(...candleSeries.map((c) => c.close));
  const range = maxPrice - minPrice || 1;
  chartCtx.beginPath();
  candleSeries.forEach((candle, idx) => {
    const x = (idx / (candleSeries.length - 1)) * width;
    const y = height - ((candle.close - minPrice) / range) * height;
    if (idx === 0) chartCtx.moveTo(x, y);
    else chartCtx.lineTo(x, y);
  });
  chartCtx.strokeStyle = '#007aff';
  chartCtx.lineWidth = 2;
  chartCtx.stroke();
}

executeTradeBtn.addEventListener('click', async () => {
  tradeErrors.textContent = '';
  const symbol = tradeSymbol.value.trim();
  const side = tradeSide.value;
  const size = parseFloat(tradeSize.value);
  const price = parseFloat(tradePrice.value);
  if (!symbol || !Number.isFinite(size) || !Number.isFinite(price)) {
    tradeErrors.textContent = 'Provide valid symbol, size, and price.';
    return;
  }
  if (configCache?.trading?.mode === 'live' && !configCache.runtime.read_only) {
    const confirmLive = confirm('Confirm live trade execution?');
    if (!confirmLive) return;
  }
  try {
    const response = await fetch('/trade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol, side, size, price })
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Trade rejected');
    }
    tradeErrors.textContent = `Trade accepted: ${JSON.stringify(data.trade)}`;
  } catch (err) {
    tradeErrors.textContent = `Error: ${err.message}`;
  }
});

loadConfig();
