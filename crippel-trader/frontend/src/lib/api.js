const BASE_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function fetchJSON(path) {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

export const endpoints = {
  settings: () => fetchJSON('/api/settings'),
  stats: () => fetchJSON('/api/stats'),
  history: (symbol) => fetchJSON(`/api/history/${symbol}`),
  assets: () => fetchJSON('/api/assets')
};
