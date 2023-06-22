import { type AssetInfo } from '@rotki/common/lib/data';

export const useAssetCacheStore = defineStore('assets/cache', () => {
  const fetchedAssetCollections: Ref<Record<string, AssetInfo>> = ref({});

  const { assetMapping } = useAssetInfoApi();

  const { cache, isPending, retrieve, reset } = useItemCache<AssetInfo>(
    async (keys: string[]) => {
      const response = await assetMapping(keys);
      return function* () {
        for (const key of keys) {
          const { assetCollections, assets } = response;
          set(fetchedAssetCollections, {
            ...get(fetchedAssetCollections),
            ...assetCollections
          });

          const item = assets[transformCase(key, true)];
          yield { item, key };
        }
      };
    }
  );

  return {
    cache,
    fetchedAssetCollections,
    isPending,
    retrieve,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useAssetCacheStore, import.meta.hot));
}
