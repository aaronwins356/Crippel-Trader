'use client';
import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { WatchlistSection } from '@/components/watchlist/WatchlistSection';
import { ComparisonSection } from '@/components/comparison/ComparisonSection';
import { fetchAssets, fetchWatchlist } from '@/lib/api';
import { useWatchlistStore } from '@/lib/store';
import { Asset, WatchlistItem } from '@/types';

export default function Dashboard() {
  const queryClient = useQueryClient();
  const { assets, addAsset, updatePrices } = useWatchlistStore();
  const [isClient, setIsClient] = useState(false);

  // Ensure we're in client-side context
  useEffect(() => {
    setIsClient(true);
  }, []);

  // Fetch all available assets
  const { data: allAssets = [] } = useQuery<Asset[]>({
    queryKey: ['assets'],
    queryFn: fetchAssets,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch watchlist symbols
  const { data: watchlistSymbols = [] } = useQuery<string[]>({
    queryKey: ['watchlist'],
    queryFn: async () => {
      const response = await fetchWatchlist();
      return response.map((item: { symbol: string }) => item.symbol);
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  // Update watchlist with full asset data
  useEffect(() => {
    if (allAssets.length > 0 && watchlistSymbols.length > 0) {
      const watchlistAssets = allAssets.filter(asset => 
        watchlistSymbols.includes(asset.symbol)
      ).map(asset => {
        // Generate mock history data for mini-chart
        const history = Array.from({ length: 30 }, (_, i) => {
          const base = asset.price;
          const variance = base * 0.02; // 2% variance
          const change = (Math.random() - 0.5) * variance;
          return base - (variance * (29 - i)) + change;
        });
        
        return {
          ...asset,
          history
        } as WatchlistItem;
      });
      
      // Update store with watchlist assets
      watchlistAssets.forEach(asset => {
        if (!assets.some(a => a.symbol === asset.symbol)) {
          addAsset(asset);
        }
      });
      
      // Update prices for existing assets
      updatePrices(watchlistAssets);
    }
  }, [allAssets, watchlistSymbols, assets, addAsset, updatePrices]);

  // Poll for price updates every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['watchlist'] });
    }, 30000);

    return () => clearInterval(interval);
  }, [queryClient]);

  if (!isClient) {
    return <div className="min-h-screen bg-slate-50 dark:bg-slate-900"></div>;
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-4 md:p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        <header className="text-center py-8">
          <h1 className="text-3xl md:text-4xl font-bold text-slate-900 dark:text-white">
            Crypto Research Dashboard
          </h1>
          <p className="text-slate-600 dark:text-slate-400 mt-2">
            Professional-grade asset tracking and comparison
          </p>
        </header>

        <WatchlistSection assets={assets} allAssets={allAssets} />
        <ComparisonSection />
      </div>
    </div>
  );
}