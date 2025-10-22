import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Plus, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface Asset {
  symbol: string;
  name: string;
  price: number;
  changePercent: number;
}

interface WatchlistItem extends Asset {
  history: number[];
}

const ALL_ASSETS: Asset[] = [
  { symbol: 'BTC', name: 'Bitcoin', price: 63742.18, changePercent: 2.51 },
  { symbol: 'ETH', name: 'Ethereum', price: 3412.77, changePercent: -0.63 },
  { symbol: 'SOL', name: 'Solana', price: 152.33, changePercent: 5.21 },
  { symbol: 'ADA', name: 'Cardano', price: 0.45, changePercent: -1.24 },
  { symbol: 'XRP', name: 'Ripple', price: 0.52, changePercent: 0.87 },
  { symbol: 'DOT', name: 'Polkadot', price: 7.21, changePercent: 3.15 },
  { symbol: 'AVAX', name: 'Avalanche', price: 36.78, changePercent: -2.31 },
  { symbol: 'MATIC', name: 'Polygon', price: 0.82, changePercent: 1.45 },
  { symbol: 'LINK', name: 'Chainlink', price: 14.56, changePercent: -0.92 },
  { symbol: 'UNI', name: 'Uniswap', price: 11.34, changePercent: 4.67 },
  { symbol: 'LTC', name: 'Litecoin', price: 82.45, changePercent: -1.78 },
  { symbol: 'BCH', name: 'Bitcoin Cash', price: 421.67, changePercent: 2.34 },
];

export const WatchlistManager = () => {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState('');

  // Load watchlist from localStorage on mount
  useEffect(() => {
    const savedWatchlist = localStorage.getItem('crypto-watchlist');
    if (savedWatchlist) {
      try {
        const parsed = JSON.parse(savedWatchlist);
        setWatchlist(parsed);
      } catch (e) {
        console.error('Error parsing watchlist from localStorage', e);
      }
    }
  }, []);

  // Save watchlist to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('crypto-watchlist', JSON.stringify(watchlist));
  }, [watchlist]);

  const addToWatchlist = (asset: Asset) => {
    // Generate mock history data for mini-chart
    const history = Array.from({ length: 30 }, (_, i) => {
      const base = asset.price;
      const variance = base * 0.02; // 2% variance
      const change = (Math.random() - 0.5) * variance;
      return base - (variance * (29 - i)) + change;
    });

    const watchlistItem: WatchlistItem = {
      ...asset,
      history
    };

    setWatchlist(prev => [...prev, watchlistItem]);
    setIsModalOpen(false);
    setSelectedAsset('');
  };

  const removeFromWatchlist = (symbol: string) => {
    setWatchlist(prev => prev.filter(item => item.symbol !== symbol));
  };

  // Format price with commas and 2 decimal places
  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(price);
  };

  // Format percentage with + or - sign
  const formatPercentage = (percentage: number) => {
    return `${percentage >= 0 ? '+' : ''}${percentage.toFixed(2)}%`;
  };

  // Determine color classes based on percentage change
  const getChangeColorClass = (percentage: number) => {
    if (percentage > 0) {
      return 'bg-green-100 dark:bg-green-900/40 text-green-600 dark:text-green-300';
    } else if (percentage < 0) {
      return 'bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-300';
    }
    return 'bg-slate-100 dark:bg-slate-700/50 text-slate-600 dark:text-slate-300';
  };

  // Get assets not in watchlist
  const availableAssets = ALL_ASSETS.filter(
    asset => !watchlist.some(item => item.symbol === asset.symbol)
  );

  return (
    <motion.section 
      className="bg-white/60 dark:bg-slate-800/60 backdrop-blur-md rounded-2xl shadow-lg p-4 md:p-6"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h2 className="text-xl font-semibold text-slate-900 dark:text-white">
            Your Watchlist
          </h2>
          <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">
            Track your favorite crypto assets
          </p>
        </div>
        
        <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Add Asset
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Asset to Watchlist</DialogTitle>
            </DialogHeader>
            <div className="py-4">
              <Select value={selectedAsset} onValueChange={setSelectedAsset}>
                <SelectTrigger>
                  <SelectValue placeholder="Select an asset" />
                </SelectTrigger>
                <SelectContent>
                  {availableAssets.map(asset => (
                    <SelectItem key={asset.symbol} value={asset.symbol}>
                      {asset.symbol} - {asset.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div className="mt-4 flex justify-end">
                <Button 
                  onClick={() => {
                    const asset = ALL_ASSETS.find(a => a.symbol === selectedAsset);
                    if (asset) {
                      addToWatchlist(asset);
                    }
                  }}
                  disabled={!selectedAsset}
                >
                  Add to Watchlist
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
      
      <AnimatePresence>
        {watchlist.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {watchlist.map((asset, index) => (
              <motion.div
                key={asset.symbol}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.2, delay: index * 0.05 }}
              >
                <Card className="bg-white dark:bg-slate-700/50 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md transition-all duration-200">
                  <CardHeader className="p-0 pb-3">
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="font-bold text-slate-900 dark:text-white text-lg">
                          {asset.symbol}
                        </CardTitle>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                          {asset.name}
                        </p>
                      </div>
                      <button
                        onClick={() => removeFromWatchlist(asset.symbol)}
                        className="text-slate-400 hover:text-red-500 transition-colors"
                        aria-label={`Remove ${asset.symbol} from watchlist`}
                      >
                        <X size={16} />
                      </button>
                    </div>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="mt-2">
                      <p className="text-lg font-semibold text-slate-900 dark:text-white">
                        {formatPrice(asset.price)}
                      </p>
                      <p className={`text-sm font-medium mt-1 px-2 py-1 rounded-full inline-block ${getChangeColorClass(asset.changePercent)}`}>
                        {asset.changePercent > 0 ? (
                          <TrendingUp size={12} className="inline mr-1" />
                        ) : asset.changePercent < 0 ? (
                          <TrendingDown size={12} className="inline mr-1" />
                        ) : (
                          <Minus size={12} className="inline mr-1" />
                        )}
                        {formatPercentage(asset.changePercent)}
                      </p>
                    </div>
                    
                    <div className="mt-4 h-16">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={asset.history.map((value, index) => ({ value, index }))}>
                          <Line
                            type="monotone"
                            dataKey="value"
                            stroke={asset.changePercent >= 0 ? "#22c55e" : "#ef4444"}
                            strokeWidth={1.5}
                            dot={false}
                            isAnimationActive={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        ) : (
          <motion.div 
            className="text-center py-12"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <p className="text-slate-500 dark:text-slate-400 mb-4">
              Your watchlist is empty
            </p>
            <Button onClick={() => setIsModalOpen(true)}>
              Add Assets
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.section>
  );
};