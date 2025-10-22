import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { WatchlistHeader } from './WatchlistHeader';
import { WatchlistTable } from './WatchlistTable';
import { AddAssetModal } from './AddAssetModal';
import { WatchlistItem, Asset } from '@/types';

interface WatchlistSectionProps {
  assets: WatchlistItem[];
  allAssets: Asset[];
}

export const WatchlistSection = ({ assets, allAssets }: WatchlistSectionProps) => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <motion.section 
      className="bg-white/60 dark:bg-slate-800/60 backdrop-blur-md rounded-2xl shadow-lg p-4 md:p-6"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <WatchlistHeader onAddAsset={() => setIsModalOpen(true)} />
      
      <AnimatePresence>
        {assets.length > 0 ? (
          <WatchlistTable assets={assets} />
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
            <button
              onClick={() => setIsModalOpen(true)}
              className="px-4 py-2 bg-slate-800 dark:bg-slate-700 text-white rounded-lg hover:bg-slate-700 dark:hover:bg-slate-600 transition-colors"
            >
              Add Assets
            </button>
          </motion.div>
        )}
      </AnimatePresence>
      
      <AddAssetModal 
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        allAssets={allAssets}
        watchlistSymbols={assets.map(a => a.symbol)}
      />
    </motion.section>
  );
};