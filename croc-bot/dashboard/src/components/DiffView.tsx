import { useEffect, useMemo, useState } from "react";

type Props = {
  diff: string;
};

const lineClass = (line: string, active: boolean) => {
  const base = "whitespace-pre-wrap text-sm font-mono px-3 py-1";
  if (line.startsWith("+++ ") || line.startsWith("--- ") || line.startsWith("@@")) {
    return `${base} bg-slate-800/60 text-slate-200 ${active ? "ring-2 ring-cyan-400" : ""}`;
  }
  if (line.startsWith("+")) {
    return `${base} bg-emerald-900/40 text-emerald-200 ${active ? "ring-2 ring-emerald-400" : ""}`;
  }
  if (line.startsWith("-")) {
    return `${base} bg-rose-900/40 text-rose-200 ${active ? "ring-2 ring-rose-400" : ""}`;
  }
  return `${base} bg-slate-900 text-slate-200 ${active ? "ring-2 ring-cyan-300" : ""}`;
};

export default function DiffView({ diff }: Props) {
  const [active, setActive] = useState(0);
  const lines = useMemo(() => diff.split(/\r?\n/), [diff]);

  useEffect(() => {
    setActive(0);
  }, [diff]);

  return (
    <div
      className="max-h-96 overflow-auto rounded-lg border border-slate-700 bg-slate-950 outline-none"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === "ArrowDown") {
          event.preventDefault();
          setActive((index) => Math.min(lines.length - 1, index + 1));
        }
        if (event.key === "ArrowUp") {
          event.preventDefault();
          setActive((index) => Math.max(0, index - 1));
        }
      }}
    >
      {lines.map((line, index) => (
        <div key={index} className={lineClass(line, index === active)}>
          <span className="select-none pr-2 text-xs text-slate-500">{index + 1}</span>
          {line}
        </div>
      ))}
    </div>
  );
}
