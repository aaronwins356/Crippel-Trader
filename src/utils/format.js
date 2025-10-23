export const formatCurrency = (value, currency = 'USD') =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 2 }).format(value);

export const formatNumber = (value, options = {}) =>
  new Intl.NumberFormat('en-US', { maximumFractionDigits: 2, ...options }).format(value);

export const formatPercent = (value, options = {}) =>
  `${value > 0 ? '+' : ''}${formatNumber(value, { maximumFractionDigits: 2, ...options })}%`;

export const classifyChange = (value) => {
  if (value > 2) return 'positive-strong';
  if (value > 0) return 'positive';
  if (value < -2) return 'negative-strong';
  if (value < 0) return 'negative';
  return 'neutral';
};
