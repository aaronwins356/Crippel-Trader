import { useEffect, useRef } from "react";
import { createChart, IChartApi, ISeriesApi, LineStyle, UTCTimestamp } from "lightweight-charts";
import type { Tick, TradeFill } from "../store";

interface Props {
  ticks: Tick[];
  fills: TradeFill[];
}

const toTimestamp = (iso: string): UTCTimestamp => Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp;

function computeSMA(values: number[], window: number): number[] {
  const result: number[] = [];
  let sum = 0;
  for (let i = 0; i < values.length; i += 1) {
    sum += values[i];
    if (i >= window) {
      sum -= values[i - window];
    }
    if (i >= window - 1) {
      result.push(sum / window);
    } else {
      result.push(values[i]);
    }
  }
  return result;
}

export default function Chart({ ticks, fills }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const priceSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const fastSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const slowSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    if (!containerRef.current || chartRef.current) {
      return;
    }
    const chart = createChart(containerRef.current, {
      layout: { background: { color: "#0f172a" }, textColor: "#cbd5f5" },
      width: containerRef.current.clientWidth,
      height: 320,
      grid: {
        vertLines: { color: "#1e293b" },
        horzLines: { color: "#1e293b" },
      },
      timeScale: { rightOffset: 12, borderColor: "#1e293b" },
    });
    chartRef.current = chart;
    const priceSeries = chart.addLineSeries({ color: "#38bdf8", lineWidth: 2 });
    const fastSeries = chart.addLineSeries({ color: "#f97316", lineWidth: 1, lineStyle: LineStyle.Dotted });
    const slowSeries = chart.addLineSeries({ color: "#a855f7", lineWidth: 1, lineStyle: LineStyle.Dashed });
    priceSeriesRef.current = priceSeries;
    fastSeriesRef.current = fastSeries;
    slowSeriesRef.current = slowSeries;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect;
        chart.applyOptions({ width });
      }
    });
    resizeObserver.observe(containerRef.current);
    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      priceSeriesRef.current = null;
      fastSeriesRef.current = null;
      slowSeriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!priceSeriesRef.current || ticks.length === 0) {
      return;
    }
    const priceSeries = priceSeriesRef.current;
    const fastSeries = fastSeriesRef.current;
    const slowSeries = slowSeriesRef.current;
    const lineData = ticks.map((tick) => ({ time: toTimestamp(tick.timestamp), value: tick.last }));
    priceSeries.setData(lineData);
    if (fastSeries && slowSeries) {
      const values = ticks.map((tick) => tick.last);
      const fast = computeSMA(values, 12).map((value, idx) => ({ time: lineData[idx].time, value }));
      const slow = computeSMA(values, 26).map((value, idx) => ({ time: lineData[idx].time, value }));
      fastSeries.setData(fast);
      slowSeries.setData(slow);
    }
    if (fills.length > 0) {
      priceSeries.setMarkers(
        fills.slice(0, 50).map((fill) => ({
          time: toTimestamp(fill.timestamp),
          position: fill.side === "buy" ? "belowBar" : "aboveBar",
          color: fill.side === "buy" ? "#22c55e" : "#f87171",
          shape: fill.side === "buy" ? "arrowUp" : "arrowDown",
          text: `${fill.side === "buy" ? "B" : "S"} ${fill.size.toFixed(3)}`,
        }))
      );
    }
  }, [ticks, fills]);

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
      <h2 className="mb-4 text-lg font-semibold">Price & Signals</h2>
      <div ref={containerRef} />
    </div>
  );
}
