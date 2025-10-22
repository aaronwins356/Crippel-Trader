import { useMemo } from 'react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { ComparisonData } from '@/types';

// Color mapping for assets
const ASSET_COLORS: Record<string, string> = {
  BTC: '#f59e0b',  // amber
  ETH: '#8b5cf6',  // violet
  SOL: '#06b6d4',  // cyan
  ADA: '#10b981',   // emerald
  XRP: '#0ea5e9',   // sky
  DOT: '#ec4899',   // pink
  AVAX: '#ef4444',  // red
  MATIC: '#8b5cf6', // violet
  LINK: '#14b8a6',  // teal
  UNI: '#6366f1',   // indigo
  LTC: '#94a3b8',   // slate
  BCH: '#00b894',   // mint
};

interface ComparisonChartProps {
  data: ComparisonData;
}

export const ComparisonChart = ({ data }: ComparisonChartProps) => {
  // Transform data for chart
  const chartData = useMemo(() => {
    if (!data.series) return [];
    
    // Get all timestamps from all series
    const allTimestamps = new Set<string>();
    Object.values(data.series).forEach(series => {
      series.forEach(point => allTimestamps.add(point.timestamp));
    });
    
    // Sort timestamps
    const sortedTimestamps = Array.from(allTimestamps).sort();
    
    // Create data points for each timestamp
    return sortedTimestamps.map(timestamp => {
      const point: Record<string, string | number> = { timestamp };
      
      // Add values for each series
      Object.entries(data.series).forEach(([symbol, series]) => {
        const seriesPoint = series.find(p => p.timestamp === timestamp);
        point[symbol] = seriesPoint ? seriesPoint.value : null;
      });
      
      return point;
    });
  }, [data]);

  // Get unique symbols for legend
  const symbols = useMemo(() => {
    return Object.keys(data.series || {});
  }, [data]);

  // Format timestamp for display
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Format value for tooltip
  const formatValue = (value: number) => {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(2)}M`;
    } else if (value >= 1000) {
      return `$${(value / 1000).toFixed(2)}K`;
    }
    return `$${value.toFixed(2)}`;
  };

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart
        data={chartData}
        margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
      >
        <CartesianGrid 
          strokeDasharray="3 3" 
          stroke="#e2e8f0" 
          strokeOpacity={0.3} 
          vertical={false} 
        />
        <XAxis
          dataKey="timestamp"
          tick={{ fontSize: 12 }}
          tickFormatter={formatTimestamp}
          tickMargin={10}
          minTickGap={50}
        />
        <YAxis
          tick={{ fontSize: 12 }}
          tickFormatter={(value) => `$${value.toLocaleString()}`}
          tickMargin={10}
          domain={['auto', 'auto']}
        />
        <Tooltip
          formatter={(value) => [formatValue(Number(value)), 'Value']}
          labelFormatter={formatTimestamp}
          contentStyle={{
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            backdropFilter: 'blur(4px)',
            borderRadius: '0.5rem',
            border: '1px solid #e2e8f0',
          }}
        />
        <Legend 
          wrapperStyle={{ paddingTop: '10px' }}
          formatter={(value) => <span className="text-slate-700 dark:text-slate-300">{value}</span>}
        />
        <ReferenceLine y={0} stroke="#000" strokeWidth={0.5} opacity={0.1} />
        
        {symbols.map(symbol => (
          <Line
            key={symbol}
            type="monotone"
            dataKey={symbol}
            stroke={ASSET_COLORS[symbol] || `hsl(${Math.random() * 360}, 70%, 50%)`}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 6 }}
            animationDuration={300}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
};