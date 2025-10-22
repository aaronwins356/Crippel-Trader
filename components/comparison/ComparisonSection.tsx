import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ComparisonHeader } from './ComparisonHeader';
import { ComparisonChart } from './ComparisonChart';
import { AssetSelector } from './AssetSelector';
import { fetchComparisonData } from '@/lib/api';
import { ComparisonData } from '@/types';

const DEFAULT_BASE_ASSET = 'BTC';
const DEFAULT_COMPARE_ASSETS = ['ETH', 'SOL'];

export const ComparisonSection = () => {
  const [baseAsset, setBaseAsset] = useState(DEFAULT_BASE_ASSET);
  const [compareAssets, setCompareAssets] = useState<string[]>(DEFAULT_COMPARE_ASSETS);
  
  const { data: comparisonData, isLoading } = useQuery<ComparisonData>({
    queryKey: ['comparison', baseAsset, compareAssets],
    queryFn: () => fetchComparisonData(baseAsset, compareAssets),
    enabled: compareAssets.length > 0,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Update localStorage when selections change
  useEffect(() => {
    localStorage.setItem('comparison-base', baseAsset);
    localStorage.setItem('comparison-assets', JSON.stringify(compareAssets));
  }, [baseAsset, compareAssets]);

  // Load from localStorage on initial render
  useEffect(() => {
    const savedBase = localStorage.getItem('comparison-base');
    const savedAssets = localStorage.getItem('comparison-assets');
    
    if (savedBase) {
      setBaseAsset(savedBase);
    }
    
    if (savedAssets) {
      try {
        setCompareAssets(JSON.parse(savedAssets));
      } catch {
        // Use defaults if parsing fails
      }
    }
  }, []);

  return (
    <section className="bg-white/60 dark:bg-slate-800/60 backdrop-blur-md rounded-2xl shadow-lg p-4 md:p-6">
      <ComparisonHeader />
      
      <AssetSelector 
        baseAsset={baseAsset}
        setBaseAsset={setBaseAsset}
        compareAssets={compareAssets}
        setCompareAssets={setCompareAssets}
      />
      
      <div className="mt-6 h-96">
        {isLoading ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-slate-500 dark:text-slate-400">Loading chart data...</div>
          </div>
        ) : comparisonData ? (
          <ComparisonChart data={comparisonData} />
        ) : (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <p className="text-slate-500 dark:text-slate-400 mb-4">
                Select assets to begin comparison
              </p>
              <p className="text-sm text-slate-400 dark:text-slate-500">
                Choose a base asset and one or more assets to compare against
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};