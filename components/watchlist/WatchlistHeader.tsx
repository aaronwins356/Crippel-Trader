import { Plus } from 'lucide-react';

interface WatchlistHeaderProps {
  onAddAsset: () => void;
}

export const WatchlistHeader = ({ onAddAsset }: WatchlistHeaderProps) => {
  return (
    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">
          Your Watchlist
        </h2>
        <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">
          Track your favorite crypto assets
        </p>
      </div>
      
      <button
        onClick={onAddAsset}
        className="flex items-center gap-2 px-4 py-2 bg-slate-800 dark:bg-slate-700 text-white rounded-lg hover:bg-slate-700 dark:hover:bg-slate-600 transition-colors self-start md:self-auto"
        aria-label="Add asset to watchlist"
      >
        <Plus size={16} />
        <span>Add Asset</span>
      </button>
    </div>
  );
};