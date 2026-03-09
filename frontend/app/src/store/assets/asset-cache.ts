import { useAssetInfoCache } from '@/modules/assets/use-asset-info-cache';

export const useAssetCacheStore = defineStore('assets/cache', () => {
  const {
    cache,
    deleteCacheKey,
    fetchedAssetCollections,
    getAssetMappingHandler,
    isPending,
    queueIdentifier,
    reset,
    resolve,
  } = useAssetInfoCache();

  return {
    cache,
    deleteCacheKey,
    fetchedAssetCollections,
    getAssetMappingHandler,
    isPending,
    queueIdentifier,
    reset,
    resolve,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAssetCacheStore, import.meta.hot));
