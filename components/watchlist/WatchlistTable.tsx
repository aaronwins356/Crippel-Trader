import { motion } from 'framer-motion';
import { WatchlistCard } from './WatchlistCard';
import { WatchlistItem } from '@/types';

interface WatchlistTableProps {
  assets: WatchlistItem[];
}

export const WatchlistTable = ({ assets }: WatchlistTableProps) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <AnimatePresence>
        {assets.map((asset, index) => (
          <motion.div
            key={asset.symbol}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2, delay: index * 0.05 }}
          >
            <WatchlistCard asset={asset} />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};