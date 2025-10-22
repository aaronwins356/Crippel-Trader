import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { WatchlistItem, WatchlistState } from '@/types';

export const useWatchlistStore = create<WatchlistState>()(
  persist(
    (set, get) => ({
      assets: [],
      addAsset: (asset) => set((state) => ({
        assets: [...state.assets, asset]
      })),
      removeAsset: (symbol) => set((state) => ({
        assets: state.assets.filter(asset => asset.symbol !== symbol)
      })),
      updatePrices: (updates) => set((state) => {
        const updatedAssets = state.assets.map(asset => {
          const update = updates.find(u => u.symbol === asset.symbol);
          return update ? { ...asset, ...update } : asset;
        });
        return { assets: updatedAssets };
      })
    }),
    {
      name: 'crypto-watchlist-storage',
      partialize: (state) => ({ assets: state.assets }),
    }
  )
);