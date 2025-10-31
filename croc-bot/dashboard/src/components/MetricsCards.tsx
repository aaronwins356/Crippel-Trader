import type { Metrics } from "../store";

interface Props {
  metrics: Metrics | null;
}

const format = (value: number, digits = 2) => value.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });

const items = [
  { key: "pnl", label: "PnL", format: (m: Metrics) => `$${format(m.pnl, 2)}` },
  { key: "sharpe", label: "Sharpe", format: (m: Metrics) => format(m.sharpe, 2) },
  { key: "win_rate", label: "Win Rate", format: (m: Metrics) => `${format(m.win_rate * 100, 1)}%` },
  { key: "exposure", label: "Exposure", format: (m: Metrics) => format(m.exposure, 3) },
  { key: "drawdown", label: "Drawdown", format: (m: Metrics) => `$${format(m.drawdown, 2)}` },
  { key: "latency_ms", label: "Latency (avg ms)", format: (m: Metrics) => format(m.latency_ms, 1) },
  { key: "loop_p99_ms", label: "Loop p99 (ms)", format: (m: Metrics) => format(m.loop_p99_ms, 1) },
  { key: "inference_p99_ms", label: "Inference p99 (ms)", format: (m: Metrics) => format(m.inference_p99_ms, 1) },
  { key: "error_rate", label: "Error Rate", format: (m: Metrics) => `${format(m.error_rate * 100, 2)}%` },
  { key: "pnl_1h", label: "PnL Δ 1h", format: (m: Metrics) => `$${format(m.pnl_1h, 2)}` },
  { key: "pnl_1d", label: "PnL Δ 1d", format: (m: Metrics) => `$${format(m.pnl_1d, 2)}` },
  { key: "drawdown_1d", label: "Drawdown 1d", format: (m: Metrics) => `$${format(m.drawdown_1d, 2)}` },
] as const;

export default function MetricsCards({ metrics }: Props) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {items.map((item) => (
        <div key={item.key} className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 shadow">
          <div className="text-sm uppercase tracking-wide text-slate-400">{item.label}</div>
          <div className="mt-2 text-2xl font-semibold text-slate-100">
            {metrics ? item.format(metrics) : "--"}
          </div>
        </div>
      ))}
    </div>
  );
}
