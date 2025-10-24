export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export const fetcher = async (url) => {
  const response = await fetch(`${API_BASE}${url}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
};

export const hireBot = async (role) => {
  const response = await fetch(`${API_BASE}/firm/hire`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role }),
  });
  if (!response.ok) {
    throw new Error("Failed to hire bot");
  }
  return response.json();
};

export const fireBot = async (botId) => {
  const response = await fetch(`${API_BASE}/firm/fire/${botId}`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error("Failed to fire bot");
  }
  return response.json();
};

export const updateAggression = async (aggression) => {
  const response = await fetch(`${API_BASE}/firm/settings/aggression`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ aggression }),
  });
  if (!response.ok) {
    throw new Error("Failed to update aggression");
  }
  return response.json();
};

export const updateMode = async (mode, confirm = false) => {
  const response = await fetch(`${API_BASE}/firm/mode`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, confirm }),
  });
  if (!response.ok) {
    throw new Error("Failed to change mode");
  }
  return response.json();
};
