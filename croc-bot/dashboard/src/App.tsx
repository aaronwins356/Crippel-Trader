import { useEffect } from "react";
import MetricsCards from "./components/MetricsCards";
import TradesTable from "./components/TradesTable";
import OrderStream from "./components/OrderStream";
import Chart from "./components/Chart";
import Controls from "./components/Controls";
import AiPanel from "./components/AiPanel";
import RlPanel from "./components/RlPanel";
import ShadowIndicator from "./components/ShadowIndicator";
import { useDashboardStore } from "./store";

function App() {
  const metrics = useDashboardStore((state) => state.metrics);
  const ticks = useDashboardStore((state) => state.ticks);
  const fills = useDashboardStore((state) => state.fills);
  const engineRunning = useDashboardStore((state) => state.engineRunning);
  useEffect(() => {
    const { loadInitial, connectStreams } = useDashboardStore.getState();
    loadInitial().catch(console.error);
    connectStreams();
  }, []);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-6 space-y-6">
      <header className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold">croc-bot dashboard</h1>
          <p className="text-slate-400">Paper trading mode with live telemetry</p>
        </div>
        <div className="text-sm text-slate-400">Engine: {engineRunning ? "Running" : "Stopped"}</div>
      </header>
      <MetricsCards metrics={metrics} />
      <ShadowIndicator />
      <div className="grid gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <Chart ticks={ticks} fills={fills} />
          <TradesTable trades={fills} />
        </div>
        <div className="space-y-6">
          <Controls />
          <RlPanel />
          <AiPanel />
          <OrderStream ticks={ticks.slice(-20)} />
        </div>
      </div>
    </div>
  );
}

export default App;
