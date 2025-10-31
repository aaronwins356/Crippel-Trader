import type { Tick } from "../store";

interface Props {
  ticks: Tick[];
}

export default function OrderStream({ ticks }: Props) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
      <h2 className="mb-4 text-lg font-semibold">Order Stream</h2>
      <div className="flex flex-col gap-2 text-sm">
        {ticks.length === 0 && <div className="text-slate-500">Awaiting ticks...</div>}
        {ticks
          .slice()
          .reverse()
          .map((tick) => (
            <div key={tick.timestamp} className="flex justify-between border-b border-slate-800 pb-1 text-slate-300">
              <span>{new Date(tick.timestamp).toLocaleTimeString()}</span>
              <span>
                {tick.last.toFixed(2)} <span className="text-slate-500">({tick.volume.toFixed(2)} vol)</span>
              </span>
            </div>
          ))}
      </div>
    </div>
  );
}
