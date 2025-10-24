import React from "react";
import useSWR from "swr";
import { fetcher } from "../lib/api";
import FirmKPI from "../components/FirmKPI";
import WorkersTable from "../components/WorkersTable";
import ModeToggle from "../components/ModeToggle";
import AggressionSlider from "../components/AggressionSlider";
import EquityChart from "../components/EquityChart";
import LogPane from "../components/LogPane";

export default function Home() {
  const { data, mutate } = useSWR("/firm/status", fetcher, { refreshInterval: 5000 });

  if (!data) {
    return (
      <main className="page">
        <h1 className="page-title">Crippel-Firm Dashboard</h1>
        <p className="muted">Loading firm status…</p>
      </main>
    );
  }

  return (
    <main className="page">
      <header className="page-header">
        <div>
          <h1 className="page-title">Crippel-Firm</h1>
          <p className="muted">Autonomous trading organization overview</p>
        </div>
        <div className="header-actions">
          <ModeToggle mode={data.mode ?? "paper"} onChange={() => mutate()} />
          <AggressionSlider aggression={data.aggression ?? 4} onChange={() => mutate()} />
        </div>
      </header>

      <FirmKPI
        equity={data.equity}
        realized={data.realized_pnl}
        unrealized={data.unrealized_pnl}
        drawdown={data.drawdown}
        conscience={data.conscience}
      />

      <section className="dashboard-grid">
        <div className="column">
          <EquityChart history={data.equity_history ?? []} />
          <WorkersTable workers={data.workers ?? []} onChange={() => mutate()} />
        </div>
        <LogPane />
      </section>
    </main>
  );
}
