import type { TradeFill } from "../store";

interface Props {
  trades: TradeFill[];
}

const formatTime = (iso: string) => new Date(iso).toLocaleTimeString();

export default function TradesTable({ trades }: Props) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Recent Trades</h2>
        <span className="text-xs text-slate-400">{trades.length} records</span>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="text-left text-slate-400">
            <tr>
              <th className="px-2 py-1">Time</th>
              <th className="px-2 py-1">Side</th>
              <th className="px-2 py-1 text-right">Size</th>
              <th className="px-2 py-1 text-right">Price</th>
              <th className="px-2 py-1 text-right">Fee</th>
            </tr>
          </thead>
          <tbody>
            {trades.slice(0, 20).map((trade) => (
              <tr key={trade.timestamp + trade.order_id} className="border-t border-slate-800 text-slate-100">
                <td className="px-2 py-1 text-slate-400">{formatTime(trade.timestamp)}</td>
                <td className={`px-2 py-1 font-semibold ${trade.side === "buy" ? "text-emerald-400" : "text-rose-400"}`}>
                  {trade.side.toUpperCase()}
                </td>
                <td className="px-2 py-1 text-right">{trade.size.toFixed(4)}</td>
                <td className="px-2 py-1 text-right">{trade.price.toFixed(2)}</td>
                <td className="px-2 py-1 text-right">{trade.fee.toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
