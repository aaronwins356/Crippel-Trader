import React from 'react';

export default function KPI({ title, value, hint, warning }) {
  return (
    <div className="card metric grid-span-3">
      <h2>{title}</h2>
      <strong>{value}</strong>
      {hint && <small>{hint}</small>}
      {warning && <span className="warning">{warning}</span>}
    </div>
  );
}
