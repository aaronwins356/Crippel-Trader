import { useEffect } from "react";
import { useDashboardStore } from "../store";

export default function ShadowIndicator() {
  const shadowStatus = useDashboardStore((state) => state.shadowStatus);
  const refreshShadowStatus = useDashboardStore((state) => state.refreshShadowStatus);

  useEffect(() => {
    const timer = setInterval(() => {
      refreshShadowStatus().catch(() => undefined);
    }, 60_000);
    return () => clearInterval(timer);
  }, [refreshShadowStatus]);

  if (!shadowStatus || Object.keys(shadowStatus).length === 0) {
    return null;
  }

  return (
    <div className="rounded border border-indigo-600 bg-indigo-500/20 px-3 py-2 text-xs text-indigo-200">
      <div className="font-semibold text-indigo-100">Shadow Mode Active</div>
      {shadowStatus.compare && <div>Compare report: {shadowStatus.compare}</div>}
      {shadowStatus.log && <div>Log: {shadowStatus.log}</div>}
    </div>
  );
}
