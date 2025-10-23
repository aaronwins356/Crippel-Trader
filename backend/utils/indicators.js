const toFixed = (value, precision = 6) => Number.parseFloat(value.toFixed(precision));

function calculateSMA(values, period) {
  if (values.length < period) return null;
  const slice = values.slice(-period);
  const sum = slice.reduce((acc, v) => acc + v, 0);
  return toFixed(sum / period, 4);
}

function calculateEMA(values, period) {
  if (values.length < period) return null;
  const k = 2 / (period + 1);
  return values.slice(-period).reduce((prev, value, index) => {
    if (index === 0) {
      return value;
    }
    return toFixed(value * k + prev * (1 - k), 4);
  }, values[values.length - period]);
}

function calculateRSI(values, period = 14) {
  if (values.length < period + 1) return null;
  let gains = 0;
  let losses = 0;
  for (let i = values.length - period; i < values.length; i += 1) {
    const change = values[i] - values[i - 1];
    if (change >= 0) gains += change; else losses -= change;
  }
  if (losses === 0) return 100;
  const rs = gains / losses;
  return toFixed(100 - 100 / (1 + rs), 2);
}

function calculateBollingerBands(values, period = 20, multiplier = 2) {
  if (values.length < period) return null;
  const slice = values.slice(-period);
  const mean = slice.reduce((acc, v) => acc + v, 0) / period;
  const variance = slice.reduce((acc, v) => acc + (v - mean) ** 2, 0) / period;
  const stdDev = Math.sqrt(variance);
  return {
    upper: toFixed(mean + multiplier * stdDev, 4),
    middle: toFixed(mean, 4),
    lower: toFixed(mean - multiplier * stdDev, 4)
  };
}

function calculateVolatility(values, period = 30) {
  if (values.length < period) return null;
  const slice = values.slice(-period);
  const mean = slice.reduce((acc, v) => acc + v, 0) / period;
  const variance = slice.reduce((acc, v) => acc + (v - mean) ** 2, 0) / period;
  return toFixed(Math.sqrt(variance), 4);
}

function calculateDrawdown(values) {
  if (!values.length) return 0;
  let peak = values[0];
  let maxDrawdown = 0;
  values.forEach((value) => {
    if (value > peak) peak = value;
    const dd = (peak - value) / peak;
    if (dd > maxDrawdown) maxDrawdown = dd;
  });
  return toFixed(maxDrawdown * 100, 2);
}

module.exports = {
  calculateSMA,
  calculateEMA,
  calculateRSI,
  calculateBollingerBands,
  calculateVolatility,
  calculateDrawdown
};
