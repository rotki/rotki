import type { AssetCollection, AssetInfo } from '@rotki/common';
import { createItemCacheStorage } from '@/modules/core/common/item-cache-storage';

/**
 * Holds the resolved name, symbol and icon data for every asset the app has looked up, plus the
 * collections those assets roll up into.
 *
 * @remarks
 * State only. `useAssetInfoCache` owns the fetching, batching and eviction, and binds to the
 * {@link ItemCacheStorage} kept here rather than holding one of its own.
 */
export const useAssetInfoCacheStore = defineStore('assets/info-cache', () => {
  const storage = createItemCacheStorage<AssetInfo>();
  const fetchedAssetCollections = shallowRef<Record<string, AssetCollection>>({});

  return {
    fetchedAssetCollections,
    storage,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAssetInfoCacheStore, import.meta.hot));
