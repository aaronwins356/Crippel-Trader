import { useEffect, useMemo, useState } from "react";
import DiffView from "./DiffView";
import { aiApply, aiRollback, aiStatus, aiSuggest, API_BASE } from "../api";

type Analysis = {
  summary: string;
  issues: Array<{ summary: string; timestamp: string }>;
  metrics: Record<string, number>;
};

type Suggestion = {
  analysis: Analysis;
  diff: string;
  model: string;
};

type SandboxStep = {
  name: string;
  status: string;
  output?: string;
};

type SandboxReport = {
  success: boolean;
  steps: SandboxStep[];
};

type StatusResponse = {
  analysis: Analysis | null;
  suggestion: (Suggestion & { prompt: string }) | null;
  report: SandboxReport | null;
  vcs: { branch?: string | null; commit?: string | null };
};

const WS_BASE = API_BASE.replace(/^http/, "ws");

export default function AiPanel() {
  const [issue, setIssue] = useState("Slow SMA loop on large datasets");
  const [context, setContext] = useState("backend/croc/strategy/rule_sma.py\nbackend/croc/runtime/engine.py");
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [diff, setDiff] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [events, setEvents] = useState<Array<{ event: string; [key: string]: unknown }>>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    aiStatus()
      .then((payload) => {
        setStatus(payload as StatusResponse);
        if ((payload as StatusResponse).suggestion?.diff) {
          setDiff((payload as StatusResponse).suggestion?.diff ?? "");
        }
      })
      .catch((err) => setError(String(err)));
  }, []);

  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/ai`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setEvents((current) => [data, ...current].slice(0, 20));
    };
    ws.onerror = () => {
      ws.close();
    };
    return () => ws.close();
  }, []);

  const analysis = useMemo(() => status?.analysis ?? status?.suggestion?.analysis ?? null, [status]);
  const report = status?.report ?? null;

  const handleSuggest = async () => {
    setLoading(true);
    setError(null);
    try {
      const suggestion = (await aiSuggest({
        issue,
        contextFiles: context
          .split(/\n+/)
          .map((line) => line.trim())
          .filter(Boolean),
      })) as Suggestion;
      setStatus((prev) => ({ ...(prev ?? { vcs: {} }), suggestion } as StatusResponse));
      setDiff(suggestion.diff);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async () => {
    setLoading(true);
    setError(null);
    try {
      const report = (await aiApply(diff)) as SandboxReport;
      const refreshed = (await aiStatus()) as StatusResponse;
      setStatus({ ...refreshed, report });
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleRollback = async () => {
    setLoading(true);
    setError(null);
    try {
      await aiRollback();
      const refreshed = (await aiStatus()) as StatusResponse;
      setStatus(refreshed);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="space-y-4 rounded-lg border border-slate-800 bg-slate-950/60 p-4">
      <header>
        <h2 className="text-lg font-semibold text-slate-100">AI Engineer</h2>
        <p className="text-sm text-slate-400">Generate, review, and apply automated fixes.</p>
      </header>
      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-300" htmlFor="ai-issue">
          Issue description
        </label>
        <textarea
          id="ai-issue"
          className="w-full rounded bg-slate-900 p-2 text-sm text-slate-100 focus:outline-none focus:ring focus:ring-cyan-500"
          value={issue}
          onChange={(event) => setIssue(event.target.value)}
          rows={3}
        />
        <label className="block text-sm font-medium text-slate-300" htmlFor="ai-context">
          Context files (one per line)
        </label>
        <textarea
          id="ai-context"
          className="w-full rounded bg-slate-900 p-2 text-sm text-slate-100 focus:outline-none focus:ring focus:ring-cyan-500"
          value={context}
          onChange={(event) => setContext(event.target.value)}
          rows={3}
        />
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded bg-cyan-600 px-3 py-2 text-sm font-semibold text-white shadow hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-50"
          onClick={handleSuggest}
          disabled={loading}
        >
          Suggest diff
        </button>
        <button
          type="button"
          className="rounded bg-emerald-600 px-3 py-2 text-sm font-semibold text-white shadow hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
          onClick={handleApply}
          disabled={loading || !diff}
        >
          Apply after checks
        </button>
        <button
          type="button"
          className="rounded bg-rose-600 px-3 py-2 text-sm font-semibold text-white shadow hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-50"
          onClick={handleRollback}
          disabled={loading || !status?.vcs?.branch}
        >
          Rollback last commit
        </button>
      </div>
      {error ? <div className="rounded bg-rose-900/40 p-3 text-sm text-rose-200">{error}</div> : null}
      {analysis ? (
        <div className="rounded border border-slate-800 bg-slate-900/60 p-3 text-sm text-slate-200">
          <div className="font-semibold text-slate-100">Analysis: {analysis.summary}</div>
          <ul className="mt-2 space-y-1 text-xs text-slate-300">
            {analysis.issues.slice(0, 5).map((issue) => (
              <li key={`${issue.timestamp}-${issue.summary}`}>{issue.summary}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {diff ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm text-slate-400">
            <span>Suggested diff ({status?.suggestion?.model ?? "model"})</span>
            {status?.vcs?.branch ? (
              <span className="text-xs text-emerald-300">Pending branch: {status.vcs.branch}</span>
            ) : null}
          </div>
          <DiffView diff={diff} />
        </div>
      ) : null}
      {report ? (
        <div className="space-y-2 text-sm text-slate-200">
          <div className="font-semibold">Sandbox checks</div>
          <ul className="space-y-1">
            {report.steps.map((step) => (
              <li
                key={step.name}
                className={`rounded border p-2 text-xs ${
                  step.status === "passed" ? "border-emerald-600/40 text-emerald-200" : "border-rose-600/40 text-rose-200"
                }`}
              >
                <div className="font-semibold uppercase">{step.name}</div>
                <div>Status: {step.status}</div>
                {step.output ? <pre className="mt-1 whitespace-pre-wrap text-[11px]">{step.output}</pre> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="space-y-2 text-sm text-slate-200">
        <div className="font-semibold">Recent events</div>
        <ul className="space-y-1 text-xs text-slate-400">
          {events.map((event, index) => (
            <li key={index} className="rounded bg-slate-900/60 p-2">
              <div className="font-semibold text-slate-200">{event.event ?? "update"}</div>
              <pre className="mt-1 whitespace-pre-wrap text-[11px]">{JSON.stringify(event, null, 2)}</pre>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
