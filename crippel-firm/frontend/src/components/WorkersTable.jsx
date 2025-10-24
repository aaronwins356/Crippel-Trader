import React from "react";
import { hireBot, fireBot } from "../lib/api";

export function WorkersTable({ workers, onChange }) {
  const handleHire = async (role) => {
    await hireBot(role);
    onChange?.();
  };

  const handleFire = async (botId) => {
    await fireBot(botId);
    onChange?.();
  };

  return (
    <section className="panel">
      <header className="panel-header">
        <h2 className="panel-title">Workers</h2>
        <div className="panel-actions">
          {[
            { label: "Research", role: "research" },
            { label: "Analyst", role: "analyst" },
            { label: "Trader", role: "trader" },
            { label: "Risk", role: "risk" },
          ].map((item) => (
            <button key={item.role} onClick={() => handleHire(item.role)} className="btn btn-success">
              Hire {item.label}
            </button>
          ))}
        </div>
      </header>
      <div className="table-scroll">
        <table className="table">
          <thead>
            <tr>
              <th>Bot ID</th>
              <th>Role</th>
              <th>Score</th>
              <th>Tenure</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {workers.length === 0 && (
              <tr>
                <td colSpan={5} className="table-empty">
                  No active workers
                </td>
              </tr>
            )}
            {workers.map((worker) => (
              <tr key={worker.bot_id}>
                <td className="mono">{worker.bot_id.slice(0, 8)}</td>
                <td className="capitalize">{worker.type}</td>
                <td>{worker.score?.toFixed(2) ?? "-"}</td>
                <td>{formatSeconds(worker.tenure)}</td>
                <td>
                  <button onClick={() => handleFire(worker.bot_id)} className="btn btn-danger">
                    Fire
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatSeconds(seconds) {
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${minutes}m ${secs}s`;
}

export default WorkersTable;
