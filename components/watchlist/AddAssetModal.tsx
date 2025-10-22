import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Search } from 'lucide-react';
import { useWatchlistStore } from '@/lib/store';
import { addAssetToWatchlist } from '@/lib/api';
import { Asset } from '@/types';

interface AddAssetModalProps {
  isOpen: boolean;
  onClose: () => void;
  allAssets: Asset[];
  watchlistSymbols: string[];
}

export const AddAssetModal = ({ 
  isOpen, 
  onClose, 
  allAssets, 
  watchlistSymbols 
}: AddAssetModalProps) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredAssets, setFilteredAssets] = useState<Asset[]>([]);
  const { addAsset } = useWatchlistStore();

  // Filter assets based on search term
  useEffect(() => {
    if (!searchTerm) {
      setFilteredAssets(allAssets.filter(asset => !watchlistSymbols.includes(asset.symbol)));
      return;
    }
    
    const term = searchTerm.toLowerCase();
    const filtered = allAssets.filter(asset => 
      (asset.symbol.toLowerCase().includes(term) || 
       asset.name.toLowerCase().includes(term)) &&
      !watchlistSymbols.includes(asset.symbol)
    );
    
    setFilteredAssets(filtered);
  }, [searchTerm, allAssets, watchlistSymbols]);

  const handleAddAsset = async (asset: Asset) => {
    try {
      await addAssetToWatchlist(asset.symbol);
      
      // Generate mock history data
      const history = Array.from({ length: 30 }, (_, i) => {
        const base = asset.price;
        const variance = base * 0.02; // 2% variance
        const change = (Math.random() - 0.5) * variance;
        return base - (variance * (29 - i)) + change;
      });
      
      addAsset({
        ...asset,
        history
      });
      
      onClose();
    } catch (error) {
      console.error('Failed to add asset:', error);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="bg-white dark:bg-slate-800 rounded-2xl w-full max-w-md max-h-[80vh] overflow-hidden flex flex-col"
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
          >
            <div className="p-6 border-b border-slate-200 dark:border-slate-700">
              <div className="flex justify-between items-center">
                <h3 className="text-xl font-bold text-slate-900 dark:text-white">
                  Add Asset
                </h3>
                <button
                  onClick={onClose}
                  className="text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
                  aria-label="Close modal"
                >
                  <X size={24} />
                </button>
              </div>
              
              <div className="relative mt-4">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" size={18} />
                <input
                  type="text"
                  placeholder="Search assets..."
                  className="w-full pl-10 pr-4 py-2 bg-slate-100 dark:bg-slate-700 rounded-lg text-slate-900 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-300 dark:focus:ring-slate-600"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>
            
            <div className="overflow-y-auto flex-1">
              {filteredAssets.length === 0 ? (
                <div className="p-6 text-center">
                  <p className="text-slate-500 dark:text-slate-400">
                    {searchTerm ? 'No assets found' : 'All available assets are already in your watchlist'}
                  </p>
                </div>
              ) : (
                <ul className="divide-y divide-slate-200 dark:divide-slate-700">
                  {filteredAssets.map((asset) => (
                    <li key={asset.symbol}>
                      <button
                        className="w-full px-6 py-4 text-left hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors flex justify-between items-center"
                        onClick={() => handleAddAsset(asset)}
                      >
                        <div>
                          <div className="font-medium text-slate-900 dark:text-white">
                            {asset.symbol}
                          </div>
                          <div className="text-sm text-slate-500 dark:text-slate-400">
                            {asset.name}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-medium text-slate-900 dark:text-white">
                            ${asset.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </div>
                          <div className={`text-sm ${asset.changePercent >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                            {asset.changePercent >= 0 ? '+' : ''}{asset.changePercent.toFixed(2)}%
                          </div>
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            
            <div className="p-4 border-t border-slate-200 dark:border-slate-700">
              <button
                onClick={onClose}
                className="w-full py-2 px-4 bg-slate-800 dark:bg-slate-700 text-white rounded-lg hover:bg-slate-700 dark:hover:bg-slate-600 transition-colors"
              >
                Close
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};