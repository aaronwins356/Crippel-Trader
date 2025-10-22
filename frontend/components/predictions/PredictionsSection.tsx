import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area } from 'recharts';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface PredictionPoint {
  date: string;
  price: number;
  lower_bound: number;
  upper_bound: number;
}

interface PredictionData {
  symbol: string;
  current_price: number;
  predictions: PredictionPoint[];
  confidence: number;
  model_accuracy: number;
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

export const PredictionsSection = () => {
  const [selectedAsset, setSelectedAsset] = useState('BTC');
  const [predictionData, setPredictionData] = useState<PredictionData | null>(null);
  const [loading, setLoading] = useState(false);
  const [timeframe, setTimeframe] = useState('30');

  useEffect(() => {
    const fetchPredictions = async () => {
      setLoading(true);
      try {
        const response = await fetch(`http://localhost:8000/predictions/${selectedAsset}?days=${timeframe}`);
        const data = await response.json();
        setPredictionData(data);
      } catch (error) {
        console.error('Error fetching predictions:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchPredictions();
  }, [selectedAsset, timeframe]);

  // Format date for display
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
    });
  };

  // Calculate price change
  const calculatePriceChange = () => {
    if (!predictionData || predictionData.predictions.length === 0) return 0;
    const firstPrice = predictionData.current_price;
    const lastPrice = predictionData.predictions[predictionData.predictions.length - 1].price;
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
          AI Price Predictions
        </h2>
        <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">
          Machine learning powered forecasts with confidence intervals
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
            Prediction Period
          </label>
          <Select value={timeframe} onValueChange={setTimeframe}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select period" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">7 Days</SelectItem>
              <SelectItem value="14">14 Days</SelectItem>
              <SelectItem value="30">30 Days</SelectItem>
              <SelectItem value="60">60 Days</SelectItem>
              <SelectItem value="90">90 Days</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {loading ? (
        <div className="h-96 flex items-center justify-center">
          <div className="text-slate-500 dark:text-slate-400">Loading predictions...</div>
        </div>
      ) : predictionData ? (
        <div className="space-y-6">
          <Card className="bg-slate-50 dark:bg-slate-700/50 border-0">
            <CardHeader>
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                  <CardTitle className="text-slate-900 dark:text-white">
                    {predictionData.symbol} Price Prediction
                  </CardTitle>
                  <CardDescription>
                    Current price: ${predictionData.current_price.toLocaleString()}
                  </CardDescription>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="secondary">
                    Confidence: {(predictionData.confidence * 100).toFixed(1)}%
                  </Badge>
                  <Badge variant="secondary">
                    Model Accuracy: {(predictionData.model_accuracy * 100).toFixed(1)}%
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 mb-4">
                <span className="text-2xl font-bold text-slate-900 dark:text-white">
                  ${predictionData.predictions[predictionData.predictions.length - 1]?.price.toLocaleString() || 'N/A'}
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
              
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={predictionData.predictions}
                    margin={{ top: 5, right: 30, left: 20, bottom: 50 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.3} />
                    <XAxis
                      dataKey="date"
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
                      formatter={(value) => [`$${Number(value).toLocaleString()}`, 'Price']}
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
                      dataKey="upper_bound"
                      fill="#8884d8"
                      fillOpacity={0.1}
                      stroke="none"
                      name="Upper Confidence"
                    />
                    <Area
                      type="monotone"
                      dataKey="lower_bound"
                      fill="#8884d8"
                      fillOpacity={0.1}
                      stroke="none"
                      name="Lower Confidence"
                    />
                    <Line
                      type="monotone"
                      dataKey="price"
                      stroke="#8884d8"
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 6 }}
                      name="Predicted Price"
                    />
                    <Line
                      type="monotone"
                      dataKey="upper_bound"
                      stroke="#8884d8"
                      strokeDasharray="3 3"
                      strokeWidth={1}
                      dot={false}
                      name="Upper Bound"
                    />
                    <Line
                      type="monotone"
                      dataKey="lower_bound"
                      stroke="#8884d8"
                      strokeDasharray="3 3"
                      strokeWidth={1}
                      dot={false}
                      name="Lower Bound"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="bg-slate-50 dark:bg-slate-700/50 border-0">
              <CardContent className="p-4">
                <div className="text-sm text-slate-600 dark:text-slate-400 mb-1">Current Price</div>
                <div className="text-xl font-bold text-slate-900 dark:text-white">
                  ${predictionData.current_price.toLocaleString()}
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-slate-50 dark:bg-slate-700/50 border-0">
              <CardContent className="p-4">
                <div className="text-sm text-slate-600 dark:text-slate-400 mb-1">Predicted Price</div>
                <div className="text-xl font-bold text-slate-900 dark:text-white">
                  ${predictionData.predictions[predictionData.predictions.length - 1]?.price.toLocaleString() || 'N/A'}
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-slate-50 dark:bg-slate-700/50 border-0">
              <CardContent className="p-4">
                <div className="text-sm text-slate-600 dark:text-slate-400 mb-1">Expected Change</div>
                <div className={`text-xl font-bold ${isPositive ? 'text-green-500' : 'text-red-500'}`}>
                  {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)}%
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      ) : (
        <div className="h-96 flex items-center justify-center">
          <div className="text-center">
            <p className="text-slate-500 dark:text-slate-400 mb-4">
              Select an asset to view AI predictions
            </p>
            <p className="text-sm text-slate-400 dark:text-slate-500">
              Our machine learning model provides price forecasts with confidence intervals
            </p>
          </div>
        </div>
      )}
    </motion.section>
  );
};