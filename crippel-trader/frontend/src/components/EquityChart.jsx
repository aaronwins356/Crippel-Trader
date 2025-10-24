import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export default function EquityChart({ data }) {
  return (
    <div className="card grid-span-6">
      <h2>Total Equity</h2>
      <div style={{ width: '100%', height: 300 }}>
        <ResponsiveContainer>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
            <XAxis dataKey="ts" stroke="#6b7280" tick={{ fontSize: 12 }} hide />
            <YAxis stroke="#6b7280" tick={{ fontSize: 12 }} domain={['auto', 'auto']} />
            <Tooltip
              contentStyle={{ background: '#111827', borderRadius: '0.75rem', border: '1px solid #1f2937' }}
            />
            <Line type="monotone" dataKey="total_equity" stroke="#38bdf8" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
