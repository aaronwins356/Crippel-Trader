import { useState } from 'react';
import { motion } from 'framer-motion';
import { X, TrendingUp, TrendingDown } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import { useWatchlistStore } from '@/lib/store';
import { removeAssetFromWatchlist } from '@/lib/api';
import { WatchlistItem } from '@/types';

interface WatchlistCardProps {
  asset: WatchlistItem;
}

export const WatchlistCard = ({ asset }: WatchlistCardProps) => {
  const [isHovered, setIsHovered] = useState(false);
  const { removeAsset } = useWatchlistStore();
  
  const handleRemove = async () => {
    try {
      await removeAssetFromWatchlist(asset.symbol);
      removeAsset(asset.symbol);
    } catch (error) {
      console.error('Failed to remove asset:', error);
    }
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

  return (
    <motion.div
      className="bg-white dark:bg-slate-700/50 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md transition-all duration-200"
      whileHover={{ scale: 1.02 }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
    >
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-slate-900 dark:text-white">{asset.symbol}</h3>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {asset.name}
            </span>
          </div>
          
          <div className="mt-2">
            <p className="text-lg font-semibold text-slate-900 dark:text-white">
              {formatPrice(asset.price)}
            </p>
            <p className={`text-sm font-medium mt-1 px-2 py-1 rounded-full inline-block ${getChangeColorClass(asset.changePercent)}`}>
              {asset.changePercent > 0 ? (
                <TrendingUp size={12} className="inline mr-1" />
              ) : asset.changePercent < 0 ? (
                <TrendingDown size={12} className="inline mr-1" />
              ) : null}
              {formatPercentage(asset.changePercent)}
            </p>
          </div>
        </div>
        
        {isHovered && (
          <motion.button
            onClick={handleRemove}
            className="text-slate-400 hover:text-red-500 transition-colors"
            aria-label={`Remove ${asset.symbol} from watchlist`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <X size={16} />
          </motion.button>
        )}
      </div>
      
      <div className="mt-4 h-12">
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
    </motion.div>
  );
};