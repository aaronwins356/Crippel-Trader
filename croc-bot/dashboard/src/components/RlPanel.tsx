import { useEffect, useMemo, useState } from "react";
import { useDashboardStore } from "../store";

interface TrainState {
  algo: string;
  seed: number;
  epochs: number;
  learning_rate: number;
  train_since?: string;
  train_until?: string;
}

export default function RlPanel() {
  const registry = useDashboardStore((state) => state.registry);
  const shadowStatus = useDashboardStore((state) => state.shadowStatus);
  const refreshRegistry = useDashboardStore((state) => state.refreshRegistry);
  const refreshShadowStatus = useDashboardStore((state) => state.refreshShadowStatus);
  const trainModel = useDashboardStore((state) => state.trainModel);
  const evaluateModel = useDashboardStore((state) => state.evaluateModel);
  const promoteModel = useDashboardStore((state) => state.promoteModel);
  const rollbackModel = useDashboardStore((state) => state.rollbackModel);
  const [trainConfig, setTrainConfig] = useState<TrainState>({ algo: "ppo", seed: 42, epochs: 10, learning_rate: 0.0003 });
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [lastMetrics, setLastMetrics] = useState<Record<string, number>>({});

  useEffect(() => {
    refreshRegistry().catch(console.error);
    refreshShadowStatus().catch(console.error);
  }, [refreshRegistry, refreshShadowStatus]);

  const versions = useMemo(() => registry?.versions ?? [], [registry]);

  useEffect(() => {
    if (!selectedVersion && versions.length > 0) {
      setSelectedVersion(versions[0].version as string);
    }
  }, [selectedVersion, versions]);

  const handleTrain = async () => {
    try {
      await trainModel(trainConfig);
      setStatusMessage("Training completed. New version registered.");
    } catch (error) {
      setStatusMessage(`Training failed: ${(error as Error).message}`);
    }
  };

  const handleEvaluate = async (shadow = false) => {
    if (!selectedVersion) {
      return;
    }
    try {
      const result = await evaluateModel({ version: selectedVersion, shadow });
      setLastMetrics(result.metrics ?? {});
      setStatusMessage(shadow ? "Shadow evaluation started." : "Evaluation complete.");
    } catch (error) {
      setStatusMessage(`Evaluation failed: ${(error as Error).message}`);
    }
  };

  const handlePromote = async () => {
    if (!selectedVersion) {
      return;
    }
    try {
      const result = await promoteModel({ version: selectedVersion, metrics: lastMetrics });
      setStatusMessage(result.passed ? "Promotion succeeded." : `Promotion blocked: ${result.reasons.join(", ")}`);
    } catch (error) {
      setStatusMessage(`Promotion failed: ${(error as Error).message}`);
    }
  };

  const handleRollback = async () => {
    try {
      await rollbackModel();
      setStatusMessage("Rollback executed. Previous version active.");
    } catch (error) {
      setStatusMessage(`Rollback failed: ${(error as Error).message}`);
    }
  };

  return (
    <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-950/60 p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Reinforcement Learning</h2>
        {registry?.active && <span className="text-xs text-slate-400">Active: {registry.active}</span>}
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <label className="text-xs uppercase tracking-wide text-slate-500">
          Algorithm
          <select
            value={trainConfig.algo}
            onChange={(event) => setTrainConfig((prev) => ({ ...prev, algo: event.target.value }))}
            className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm"
          >
            <option value="ppo">PPO</option>
            <option value="ddpg">DDPG</option>
          </select>
        </label>
        <label className="text-xs uppercase tracking-wide text-slate-500">
          Seed
          <input
            type="number"
            value={trainConfig.seed}
            onChange={(event) => setTrainConfig((prev) => ({ ...prev, seed: Number(event.target.value) }))}
            className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm"
          />
        </label>
        <label className="text-xs uppercase tracking-wide text-slate-500">
          Epochs
          <input
            type="number"
            value={trainConfig.epochs}
            onChange={(event) => setTrainConfig((prev) => ({ ...prev, epochs: Number(event.target.value) }))}
            className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm"
          />
        </label>
        <label className="text-xs uppercase tracking-wide text-slate-500">
          Learning Rate
          <input
            type="number"
            step="0.0001"
            value={trainConfig.learning_rate}
            onChange={(event) => setTrainConfig((prev) => ({ ...prev, learning_rate: Number(event.target.value) }))}
            className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm"
          />
        </label>
      </div>
      <button
        type="button"
        onClick={() => handleTrain().catch(console.error)}
        className="w-full rounded bg-emerald-500 px-3 py-2 text-sm font-semibold text-slate-900 hover:bg-emerald-400"
      >
        Train Model
      </button>
      <div className="space-y-2">
        <label className="text-xs uppercase tracking-wide text-slate-500">
          Candidate Version
          <select
            value={selectedVersion ?? ""}
            onChange={(event) => setSelectedVersion(event.target.value)}
            className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm"
          >
            {versions.map((item) => (
              <option key={item.version} value={item.version as string}>
                {item.version}
              </option>
            ))}
          </select>
        </label>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => handleEvaluate(false).catch(console.error)}
            className="flex-1 rounded border border-sky-500 px-3 py-2 text-sm font-semibold text-sky-400 hover:bg-sky-500/10"
          >
            Evaluate
          </button>
          <button
            type="button"
            onClick={() => handleEvaluate(true).catch(console.error)}
            className="flex-1 rounded border border-indigo-500 px-3 py-2 text-sm font-semibold text-indigo-300 hover:bg-indigo-500/10"
          >
            Shadow
          </button>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => handlePromote().catch(console.error)}
            className="flex-1 rounded bg-emerald-600 px-3 py-2 text-sm font-semibold text-slate-900 hover:bg-emerald-500"
          >
            Promote
          </button>
          <button
            type="button"
            onClick={() => handleRollback().catch(console.error)}
            className="flex-1 rounded bg-rose-500 px-3 py-2 text-sm font-semibold text-slate-900 hover:bg-rose-400"
          >
            Rollback
          </button>
        </div>
      </div>
      {statusMessage && <div className="text-xs text-slate-300">{statusMessage}</div>}
      {shadowStatus && shadowStatus.log && (
        <div className="rounded border border-slate-800 bg-slate-900/60 p-3 text-xs text-slate-300">
          <div className="font-semibold text-slate-200">Shadow Run</div>
          <div>Log: {shadowStatus.log}</div>
          {shadowStatus.compare && <div>Compare: {shadowStatus.compare}</div>}
          {shadowStatus.started_at && <div>Started: {shadowStatus.started_at}</div>}
        </div>
      )}
      <div className="space-y-2">
        <div className="text-xs uppercase tracking-wide text-slate-500">Registered Versions</div>
        <div className="space-y-1 text-xs text-slate-300">
          {versions.map((item) => {
            const sharpeValue = typeof item.metrics?.sharpe === "number" ? (item.metrics.sharpe as number) : null;
            return (
              <div key={item.version} className="flex justify-between rounded border border-slate-800 bg-slate-900/60 px-2 py-1">
                <span>{item.version}</span>
                <span className="text-slate-500">{sharpeValue !== null ? sharpeValue.toFixed(2) : "--"}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
