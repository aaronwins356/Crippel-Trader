export const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  if (response.status === 204) {
    return {} as T;
  }
  return (await response.json()) as T;
}

export function fetchConfig() {
  return request("/config");
}

export function fetchMetrics() {
  return request("/metrics");
}

export function fetchHealth() {
  return request("/healthz");
}

export function startEngine() {
  return request("/controls/start", { method: "POST" });
}

export function stopEngine() {
  return request("/controls/stop", { method: "POST" });
}

export function setKillSwitch(active: boolean) {
  return request("/controls/kill-switch", {
    method: "POST",
    body: JSON.stringify({ active }),
  });
}

export function setModel(path: string) {
  return request("/controls/model", {
    method: "POST",
    body: JSON.stringify({ path }),
  });
}

export function setRiskLimits(risk: { max_position: number; max_notional: number; max_daily_drawdown: number }) {
  return request("/controls/risk", {
    method: "POST",
    body: JSON.stringify(risk),
  });
}

export function triggerTraining(payload: {
  algo: string;
  seed: number;
  epochs: number;
  learning_rate: number;
  train_since?: string | null;
  train_until?: string | null;
}) {
  return request("/rl/train", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function triggerEvaluation(payload: { version?: string | null; shadow?: boolean }) {
  return request("/rl/evaluate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function triggerPromotion(payload: { version: string; metrics: Record<string, number> }) {
  return request("/rl/promote", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function triggerRollback(version?: string) {
  return request("/rl/rollback", {
    method: "POST",
    body: JSON.stringify({ version: version ?? null }),
  });
}

export function fetchRegistry() {
  return request("/rl/registry");
}

export function fetchShadowStatus() {
  return request("/rl/shadow_status");
}

export function aiSuggest(payload: { issue: string; contextFiles?: string[] }) {
  return request("/ai/suggest", {
    method: "POST",
    body: JSON.stringify({ issue: payload.issue, contextFiles: payload.contextFiles ?? [] }),
  });
}

export function aiApply(diff: string, allowAddDep = false) {
  return request("/ai/apply", {
    method: "POST",
    body: JSON.stringify({ diff, allow_add_dep: allowAddDep }),
  });
}

export function aiRollback() {
  return request("/ai/rollback", { method: "POST" });
}

export function aiStatus() {
  return request("/ai/status");
}
