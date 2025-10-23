const toFixed = (value, precision = 6) => Number.parseFloat(value.toFixed(precision));

export function calculateSMA(values, period) {
  if (values.length < period) return null;
  const slice = values.slice(-period);
  const sum = slice.reduce((acc, v) => acc + v, 0);
  return toFixed(sum / period, 4);
}

export function calculateEMA(values, period) {
  if (values.length < period) return null;
  let ema = values[values.length - period];
  const multiplier = 2 / (period + 1);
  for (let i = values.length - period + 1; i < values.length; i += 1) {
    ema = (values[i] - ema) * multiplier + ema;
  }
  return toFixed(ema, 4);
}

export function calculateRSI(values, period = 14) {
  if (values.length < period + 1) return null;
  let gains = 0;
  let losses = 0;
  for (let i = values.length - period + 1; i < values.length; i += 1) {
    const change = values[i] - values[i - 1];
    if (change >= 0) gains += change;
    else losses -= change;
  }
  if (losses === 0) return 100;
  const rs = gains / losses;
  return toFixed(100 - 100 / (1 + rs), 2);
}

export function calculateMACD(values, fast = 12, slow = 26, signal = 9) {
  if (values.length < slow + signal) return null;
  const emaFastValues = [];
  const emaSlowValues = [];
  let emaFast = values[0];
  let emaSlow = values[0];
  const kFast = 2 / (fast + 1);
  const kSlow = 2 / (slow + 1);
  values.forEach((price) => {
    emaFast = price * kFast + emaFast * (1 - kFast);
    emaSlow = price * kSlow + emaSlow * (1 - kSlow);
    emaFastValues.push(emaFast);
    emaSlowValues.push(emaSlow);
  });
  const macdLine = emaFastValues.map((fastValue, index) => fastValue - emaSlowValues[index]);
  let signalLine = macdLine[slow - 1];
  const signalValues = [];
  const kSignal = 2 / (signal + 1);
  for (let i = slow; i < macdLine.length; i += 1) {
    signalLine = macdLine[i] * kSignal + signalLine * (1 - kSignal);
    signalValues.push(signalLine);
  }
  const histogram = macdLine.slice(-(signalValues.length)).map((value, idx) => value - signalValues[idx]);
  return {
    macd: toFixed(macdLine[macdLine.length - 1], 4),
    signal: toFixed(signalValues[signalValues.length - 1], 4),
    histogram: toFixed(histogram[histogram.length - 1], 4)
  };
}

export function calculateVolatility(values, period = 30) {
  if (values.length < period) return null;
  const slice = values.slice(-period);
  const mean = slice.reduce((acc, value) => acc + value, 0) / period;
  const variance = slice.reduce((acc, value) => acc + (value - mean) ** 2, 0) / period;
  return toFixed(Math.sqrt(variance), 4);
}

export function calculateBollingerBands(values, period = 20, multiplier = 2) {
  if (values.length < period) return null;
  const slice = values.slice(-period);
  const mean = slice.reduce((acc, value) => acc + value, 0) / period;
  const variance = slice.reduce((acc, value) => acc + (value - mean) ** 2, 0) / period;
  const stdDev = Math.sqrt(variance);
  return {
    upper: toFixed(mean + multiplier * stdDev, 4),
    middle: toFixed(mean, 4),
    lower: toFixed(mean - multiplier * stdDev, 4)
  };
}

export function calculateDrawdown(values) {
  if (!values.length) return 0;
  let peak = values[0];
  let maxDrawdown = 0;
  values.forEach((value) => {
    if (value > peak) peak = value;
    const drawdown = (peak - value) / peak;
    if (drawdown > maxDrawdown) maxDrawdown = drawdown;
  });
  return toFixed(maxDrawdown * 100, 2);
}

export function normalizeNumber(value, digits = 2) {
  if (value === null || Number.isNaN(value)) return null;
  return Number.parseFloat(Number(value).toFixed(digits));
}

export default {
  calculateSMA,
  calculateEMA,
  calculateRSI,
  calculateMACD,
  calculateVolatility,
  calculateBollingerBands,
  calculateDrawdown,
  normalizeNumber
};
