// API utility functions
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

// Generic fetch helper
const apiFetch = async (endpoint: string, options: RequestInit = {}) => {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  });
  
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  
  return response.json();
};

// Asset API functions
export const fetchAssets = () => {
  return apiFetch('/assets');
};

export const fetchWatchlist = () => {
  return apiFetch('/watchlist');
};

export const addAssetToWatchlist = (symbol: string) => {
  return apiFetch('/watchlist', {
    method: 'POST',
    body: JSON.stringify({ symbol }),
  });
};

export const removeAssetFromWatchlist = (symbol: string) => {
  return apiFetch(`/watchlist/${symbol}`, {
    method: 'DELETE',
  });
};

export const fetchComparisonData = (base: string, compare: string[]) => {
  const queryParams = new URLSearchParams({
    base,
    compare: compare.join(','),
  });
  
  return apiFetch(`/comparison?${queryParams}`);
};