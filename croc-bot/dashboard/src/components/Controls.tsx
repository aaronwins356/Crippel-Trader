import { useEffect, useState } from "react";
import { useDashboardStore } from "../store";

export default function Controls() {
  const engineRunning = useDashboardStore((state) => state.engineRunning);
  const start = useDashboardStore((state) => state.start);
  const stop = useDashboardStore((state) => state.stop);
  const killSwitch = useDashboardStore((state) => state.killSwitch);
  const toggleKillSwitch = useDashboardStore((state) => state.toggleKillSwitch);
  const riskLimits = useDashboardStore((state) => state.riskLimits);
  const updateRisk = useDashboardStore((state) => state.updateRisk);
  const activateModel = useDashboardStore((state) => state.activateModel);

  const [modelPath, setModelPath] = useState("");
  const [riskDraft, setRiskDraft] = useState({ max_position: 1, max_notional: 10000, max_daily_drawdown: 500 });

  useEffect(() => {
    if (riskLimits) {
      setRiskDraft(riskLimits);
    }
  }, [riskLimits]);

  return (
    <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-950/60 p-4">
      <h2 className="text-lg font-semibold">Controls</h2>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => start().catch(console.error)}
          className="flex-1 rounded bg-emerald-500 px-3 py-2 text-sm font-semibold text-slate-900 hover:bg-emerald-400"
          disabled={engineRunning}
        >
          Start
        </button>
        <button
          type="button"
          onClick={() => stop().catch(console.error)}
          className="flex-1 rounded bg-rose-500 px-3 py-2 text-sm font-semibold text-slate-900 hover:bg-rose-400"
          disabled={!engineRunning}
        >
          Stop
        </button>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-300">Kill switch</span>
        <label className="inline-flex cursor-pointer items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={killSwitch}
            onChange={(event) => toggleKillSwitch(event.target.checked).catch(console.error)}
            className="h-4 w-4"
          />
          <span>{killSwitch ? "Active" : "Safe"}</span>
        </label>
      </div>
      <div className="space-y-3">
        <div className="text-sm font-semibold text-slate-300">Risk Limits</div>
        <label className="block text-xs uppercase tracking-wide text-slate-500">
          Max Position {riskDraft.max_position.toFixed(2)}
          <input
            type="range"
            min={0.1}
            max={10}
            step={0.1}
            value={riskDraft.max_position}
            onChange={(event) => setRiskDraft((prev) => ({ ...prev, max_position: Number(event.target.value) }))}
            className="mt-1 w-full"
          />
        </label>
        <label className="block text-xs uppercase tracking-wide text-slate-500">
          Max Notional ${riskDraft.max_notional.toFixed(0)}
          <input
            type="range"
            min={1_000}
            max={100_000}
            step={1_000}
            value={riskDraft.max_notional}
            onChange={(event) => setRiskDraft((prev) => ({ ...prev, max_notional: Number(event.target.value) }))}
            className="mt-1 w-full"
          />
        </label>
        <label className="block text-xs uppercase tracking-wide text-slate-500">
          Max Daily Drawdown ${riskDraft.max_daily_drawdown.toFixed(0)}
          <input
            type="range"
            min={50}
            max={5_000}
            step={50}
            value={riskDraft.max_daily_drawdown}
            onChange={(event) =>
              setRiskDraft((prev) => ({ ...prev, max_daily_drawdown: Number(event.target.value) }))
            }
            className="mt-1 w-full"
          />
        </label>
        <button
          type="button"
          onClick={() => updateRisk(riskDraft).catch(console.error)}
          className="w-full rounded border border-emerald-500 px-3 py-2 text-sm font-semibold text-emerald-400 hover:bg-emerald-500/10"
        >
          Apply Risk Limits
        </button>
      </div>
      <div className="space-y-2">
        <label className="block text-xs uppercase tracking-wide text-slate-500">
          Model Path
          <input
            type="text"
            value={modelPath}
            onChange={(event) => setModelPath(event.target.value)}
            placeholder="/absolute/path/to/model.pt"
            className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100"
          />
        </label>
        <button
          type="button"
          onClick={() => modelPath && activateModel(modelPath).catch(console.error)}
          className="w-full rounded border border-sky-500 px-3 py-2 text-sm font-semibold text-sky-400 hover:bg-sky-500/10"
        >
          Activate Model
        </button>
      </div>
    </div>
  );
}
