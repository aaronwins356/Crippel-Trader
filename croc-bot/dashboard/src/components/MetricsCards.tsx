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
  { key: "latency_ms", label: "Latency (ms)", format: (m: Metrics) => format(m.latency_ms, 1) },
] as const;

export default function MetricsCards({ metrics }: Props) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
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
