import React, { useMemo } from "react";
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LinearScale,
  TimeScale,
  Tooltip,
  Legend,
} from "chart.js";
import "chartjs-adapter-date-fns";
import { Line } from "react-chartjs-2";

ChartJS.register(LineElement, PointElement, LinearScale, TimeScale, Tooltip, Legend);

export function EquityChart({ history }) {
  const data = useMemo(() => {
    const points = history.map(([ts, value]) => ({ x: new Date(ts), y: value }));
    return {
      datasets: [
        {
          label: "Equity",
          data: points,
          borderColor: "#10b981",
          backgroundColor: "rgba(16, 185, 129, 0.2)",
          tension: 0.25,
        },
      ],
    };
  }, [history]);

  const options = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          type: "time",
          time: { unit: "minute" },
          ticks: { color: "#94a3b8" },
          grid: { color: "rgba(148, 163, 184, 0.1)" },
        },
        y: {
          ticks: { color: "#94a3b8" },
          grid: { color: "rgba(148, 163, 184, 0.1)" },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (context) => `$${context.parsed.y.toFixed(2)}`,
          },
        },
      },
    }),
    []
  );

  return (
    <div className="panel chart-panel">
      <Line data={data} options={options} />
    </div>
  );
}

export default EquityChart;
