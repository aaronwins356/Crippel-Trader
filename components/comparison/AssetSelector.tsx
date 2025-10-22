import { useState } from 'react';
import { motion } from 'framer-motion';
import { X } from 'lucide-react';

interface AssetSelectorProps {
  baseAsset: string;
  setBaseAsset: (asset: string) => void;
  compareAssets: string[];
  setCompareAssets: (assets: string[]) => void;
}

export const AssetSelector = ({
  baseAsset,
  setBaseAsset,
  compareAssets,
  setCompareAssets
}: AssetSelectorProps) => {
  const [newCompareAsset, setNewCompareAsset] = useState('');

  const availableAssets = ['BTC', 'ETH', 'SOL', 'ADA', 'XRP', 'DOT', 'AVAX', 'MATIC', 'LINK', 'UNI', 'LTC', 'BCH'];
  
  const handleAddCompareAsset = () => {
    if (newCompareAsset && !compareAssets.includes(newCompareAsset) && newCompareAsset !== baseAsset) {
      setCompareAssets([...compareAssets, newCompareAsset]);
      setNewCompareAsset('');
    }
  };

  const handleRemoveCompareAsset = (asset: string) => {
    setCompareAssets(compareAssets.filter(a => a !== asset));
  };

  const handleBaseAssetChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newBase = e.target.value;
    setBaseAsset(newBase);
    
    // If the new base was in compare assets, remove it
    if (compareAssets.includes(newBase)) {
      setCompareAssets(compareAssets.filter(a => a !== newBase));
    }
    
    // If the old base wasn't in compare assets and isn't the new base, add it
    if (!compareAssets.includes(baseAsset) && baseAsset !== newBase) {
      setCompareAssets([...compareAssets, baseAsset]);
    }
  };

  return (
    <div className="flex flex-col md:flex-row gap-4">
      <div className="flex-1">
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
          Base Asset
        </label>
        <select
          value={baseAsset}
          onChange={handleBaseAssetChange}
          className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-slate-300 dark:focus:ring-slate-600"
        >
          {availableAssets.map(asset => (
            <option key={asset} value={asset}>{asset}</option>
          ))}
        </select>
      </div>
      
      <div className="flex-1">
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
          Compare Against
        </label>
        <div className="flex gap-2">
          <select
            value={newCompareAsset}
            onChange={(e) => setNewCompareAsset(e.target.value)}
            className="flex-1 px-3 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-slate-300 dark:focus:ring-slate-600"
          >
            <option value="">Select asset</option>
            {availableAssets
              .filter(asset => asset !== baseAsset && !compareAssets.includes(asset))
              .map(asset => (
                <option key={asset} value={asset}>{asset}</option>
              ))}
          </select>
          <button
            onClick={handleAddCompareAsset}
            disabled={!newCompareAsset}
            className="px-4 py-2 bg-slate-800 dark:bg-slate-700 text-white rounded-lg hover:bg-slate-700 dark:hover:bg-slate-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Add
          </button>
        </div>
        
        <div className="mt-2 flex flex-wrap gap-2">
          {compareAssets.map(asset => (
            <motion.div
              key={asset}
              className="flex items-center gap-1 px-3 py-1 bg-slate-100 dark:bg-slate-700 rounded-full text-sm"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
            >
              <span className="text-slate-900 dark:text-white">{asset}</span>
              <button
                onClick={() => handleRemoveCompareAsset(asset)}
                className="text-slate-500 hover:text-slate-900 dark:hover:text-white"
                aria-label={`Remove ${asset}`}
              >
                <X size={14} />
              </button>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};