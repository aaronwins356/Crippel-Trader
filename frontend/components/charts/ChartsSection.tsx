import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface ChartDataPoint {
  timestamp: string;
  price: number;
  volume?: number;
}

interface ChartData {
  symbol: string;
  data: ChartDataPoint[];
  timeframe: string;
}

const ASSETS = [
  { symbol: 'BTC', name: 'Bitcoin' },
  { symbol: 'ETH', name: 'Ethereum' },
  { symbol: 'SOL', name: 'Solana' },
  { symbol: 'ADA', name: 'Cardano' },
  { symbol: 'XRP', name: 'Ripple' },
  { symbol: 'DOT', name: 'Polkadot' },
  { symbol: 'AVAX', name: 'Avalanche' },
  { symbol: 'MATIC', name: 'Polygon' },
  { symbol: 'LINK', name: 'Chainlink' },
  { symbol: 'UNI', name: 'Uniswap' },
];

const TIMEFRAMES = [
  { value: '1d', label: '24 Hours' },
  { value: '7d', label: '7 Days' },
  { value: '30d', label: '30 Days' },
  { value: '90d', label: '90 Days' },
  { value: '1y', label: '1 Year' },
];

export const ChartsSection = () => {
  const [selectedAsset, setSelectedAsset] = useState('BTC');
  const [timeframe, setTimeframe] = useState('7d');
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchChartData = async () => {
      setLoading(true);
      try {
        const response = await fetch(`http://localhost:8000/charts/${selectedAsset}?timeframe=${timeframe}`);
        const data = await response.json();
        setChartData(data);
      } catch (error) {
        console.error('Error fetching chart data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchChartData();
  }, [selectedAsset, timeframe]);

  // Format date for display
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    
    if (timeframe === '1d') {
      return date.toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
      });
    }
    
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
    });
  };

  // Calculate price change
  const calculatePriceChange = () => {
    if (!chartData || chartData.data.length < 2) return 0;
    const firstPrice = chartData.data[0].price;
    const lastPrice = chartData.data[chartData.data.length - 1].price;
    return ((lastPrice - firstPrice) / firstPrice) * 100;
  };

  const priceChange = calculatePriceChange();
  const isPositive = priceChange > 0;

  return (
    <motion.section 
      className="bg-white/60 dark:bg-slate-800/60 backdrop-blur-md rounded-2xl shadow-lg p-4 md:p-6"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">
          Price Charts
        </h2>
        <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">
          Interactive price charts with volume data
        </p>
      </div>

      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="flex-1">
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Select Asset
          </label>
          <Select value={selectedAsset} onValueChange={setSelectedAsset}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select asset" />
            </SelectTrigger>
            <SelectContent>
              {ASSETS.map((asset) => (
                <SelectItem key={asset.symbol} value={asset.symbol}>
                  {asset.symbol} - {asset.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        <div className="flex-1">
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Timeframe
          </label>
          <Select value={timeframe} onValueChange={setTimeframe}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select timeframe" />
            </SelectTrigger>
            <SelectContent>
              {TIMEFRAMES.map((tf) => (
                <SelectItem key={tf.value} value={tf.value}>
                  {tf.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {loading ? (
        <div className="h-96 flex items-center justify-center">
          <div className="text-slate-500 dark:text-slate-400">Loading chart data...</div>
        </div>
      ) : chartData ? (
        <Card className="bg-slate-50 dark:bg-slate-700/50 border-0">
          <CardHeader>
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <CardTitle className="text-slate-900 dark:text-white">
                  {chartData.symbol} Price Chart
                </CardTitle>
                <CardDescription>
                  {TIMEFRAMES.find(tf => tf.value === timeframe)?.label} price movement
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold text-slate-900 dark:text-white">
                  ${chartData.data.length > 0 ? chartData.data[chartData.data.length - 1].price.toLocaleString() : 'N/A'}
                </span>
                <div className={`flex items-center gap-1 ${isPositive ? 'text-green-500' : 'text-red-500'}`}>
                  {isPositive ? (
                    <TrendingUp className="h-4 w-4" />
                  ) : priceChange < 0 ? (
                    <TrendingDown className="h-4 w-4" />
                  ) : (
                    <Minus className="h-4 w-4" />
                  )}
                  <span className="font-medium">
                    {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={chartData.data}
                  margin={{ top: 5, right: 30, left: 20, bottom: 50 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.3} />
                  <XAxis
                    dataKey="timestamp"
                    tick={{ fontSize: 12 }}
                    tickFormatter={formatDate}
                    tickMargin={10}
                  />
                  <YAxis
                    domain={['auto', 'auto']}
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => `$${value.toLocaleString()}`}
                    tickMargin={10}
                  />
                  <Tooltip
                    formatter={(value, name) => {
                      if (name === 'price') {
                        return [`$${Number(value).toLocaleString()}`, 'Price'];
                      }
                      return [Number(value).toLocaleString(), 'Volume'];
                    }}
                    labelFormatter={formatDate}
                    contentStyle={{
                      backgroundColor: 'rgba(255, 255, 255, 0.9)',
                      backdropFilter: 'blur(4px)',
                      borderRadius: '0.5rem',
                      border: '1px solid #e2e8f0',
                    }}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="price"
                    stroke="#8884d8"
                    fill="#8884d8"
                    fillOpacity={0.2}
                    strokeWidth={2}
                    name="Price"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="h-96 flex items-center justify-center">
          <div className="text-center">
            <p className="text-slate-500 dark:text-slate-400 mb-4">
              Select an asset and timeframe to view chart
            </p>
            <p className="text-sm text-slate-400 dark:text-slate-500">
              Interactive price charts with historical data
            </p>
          </div>
        </div>
      )}
    </motion.section>
  );
};