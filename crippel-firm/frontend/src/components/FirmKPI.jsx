import React from "react";

const formatPct = (value) => `${(value * 100).toFixed(2)}%`;

export function FirmKPI({ equity, realized, unrealized, drawdown, conscience }) {
  return (
    <section className="kpi-grid">
      <KpiCard title="Equity" value={`$${equity.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
      <KpiCard
        title="Realized PnL"
        value={`$${realized.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
      />
      <KpiCard
        title="Unrealized PnL"
        value={`$${unrealized.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
      />
      <KpiCard title="Drawdown" value={formatPct(drawdown)} trend={drawdown > 0.1 ? "down" : "up"} />
      <KpiCard title="Conscience" value={`$${conscience.toFixed(2)}`} />
    </section>
  );
}

function KpiCard({ title, value, trend }) {
  return (
    <div className="panel">
      <p className="panel-label">{title}</p>
      <p className="panel-value">{value}</p>
      {trend && <span className={`trend trend-${trend}`}>{trend === "up" ? "Improving" : "Worsening"}</span>}
    </div>
  );
}

export default FirmKPI;
