import create from "zustand";
import {
  fetchConfig,
  fetchMetrics,
  fetchHealth,
  setKillSwitch,
  setModel,
  setRiskLimits,
  startEngine,
  stopEngine,
} from "./api";

export interface Metrics {
  pnl: number;
  sharpe: number;
  win_rate: number;
  exposure: number;
  drawdown: number;
  latency_ms: number;
}

export interface TradeFill {
  order_id: string;
  side: string;
  size: number;
  price: number;
  fee: number;
  timestamp: string;
}

export interface Tick {
  timestamp: string;
  bid: number;
  ask: number;
  last: number;
  volume: number;
}

interface DashboardState {
  metrics: Metrics | null;
  fills: TradeFill[];
  ticks: Tick[];
  config: any | null;
  riskLimits: { max_position: number; max_notional: number; max_daily_drawdown: number } | null;
  engineRunning: boolean;
  killSwitch: boolean;
  mode: "paper" | "live";
  connected: boolean;
  loadInitial: () => Promise<void>;
  connectStreams: () => void;
  start: () => Promise<void>;
  stop: () => Promise<void>;
  toggleKillSwitch: (active: boolean) => Promise<void>;
  activateModel: (path: string) => Promise<void>;
  updateRisk: (risk: { max_position: number; max_notional: number; max_daily_drawdown: number }) => Promise<void>;
}

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");

export const useDashboardStore = create<DashboardState>()((set, get) => ({
    metrics: null,
    fills: [],
    ticks: [],
    config: null,
    riskLimits: null,
    engineRunning: false,
    killSwitch: false,
    mode: "paper",
    connected: false,
    loadInitial: async () => {
      const [config, metrics, health] = await Promise.all([fetchConfig(), fetchMetrics(), fetchHealth()]);
      set({
        config,
        metrics,
        engineRunning: Boolean(health?.engine_running),
        mode: (health?.mode as "paper" | "live") ?? "paper",
        riskLimits: config?.risk ?? null,
      });
    },
    connectStreams: () => {
      if (get().connected) {
        return;
      }
      const topics: Array<"ticks" | "fills" | "metrics"> = ["ticks", "fills", "metrics"];
      topics.forEach((topic) => {
        const ws = new WebSocket(`${WS_BASE}/ws/stream?topic=${topic}`);
        ws.onmessage = (event) => {
          const payload = JSON.parse(event.data);
          const data = payload.data;
          set((state) => {
            if (topic === "metrics") {
              return { metrics: data };
            }
            if (topic === "fills") {
              const fills = [data as TradeFill, ...state.fills].slice(0, 200);
              return { fills };
            }
            const ticks = [...state.ticks.slice(-400), data as Tick];
            return { ticks };
          });
        };
        ws.onerror = () => {
          ws.close();
        };
      });
      set({ connected: true });
    },
    start: async () => {
      await startEngine();
      set({ engineRunning: true });
    },
    stop: async () => {
      await stopEngine();
      set({ engineRunning: false });
    },
    toggleKillSwitch: async (active: boolean) => {
      await setKillSwitch(active);
      set({ killSwitch: active });
    },
    activateModel: async (path: string) => {
      await setModel(path);
    },
    updateRisk: async (risk) => {
      const updated = await setRiskLimits(risk);
      set({ riskLimits: updated });
    },
}));
