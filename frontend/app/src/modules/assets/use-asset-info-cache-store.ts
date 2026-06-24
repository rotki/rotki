import type { AssetCollection, AssetInfo } from '@rotki/common';
import { createItemCacheStorage } from '@/modules/core/common/use-item-cache';

/**
 * Pure-state store for the asset-info cache. Holds only the persistent storage
 * containers; the fetch/debounce/LRU logic lives in useAssetInfoCache, which
 * binds to this so the cache survives composable teardown instead of being wiped
 * at zero subscribers.
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
