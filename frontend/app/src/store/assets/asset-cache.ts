import type { AssetInfo } from '@rotki/common';
import type { AssetMap } from '@/types/asset';

export const useAssetCacheStore = defineStore('assets/cache', () => {
  const fetchedAssetCollections = ref<Record<string, AssetInfo>>({});

  const { assetMapping } = useAssetInfoApi();
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const getAssetMappingHandler = async (identifiers: string[]): Promise<AssetMap> => {
    try {
      return await assetMapping(identifiers);
    }
    catch (error: any) {
      notify({
        title: t('asset_search.error.title'),
        message: t('asset_search.error.message', {
          message: error.message,
        }),
        display: true,
      });
      return {
        assetCollections: {},
        assets: {},
      };
    }
  };

  const { cache, isPending, retrieve, reset, deleteCacheKey, queueIdentifier } = useItemCache<AssetInfo>(
    async (keys: string[]) => {
      const response = await getAssetMappingHandler(keys);
      return function* (): Generator<{ item: AssetInfo; key: string }, void> {
        for (const key of keys) {
          const { assetCollections, assets } = response;
          set(fetchedAssetCollections, {
            ...get(fetchedAssetCollections),
            ...assetCollections,
          });

          const item = assets[transformCase(key, true)];
          yield { item, key };
        }
      };
    },
  );

  return {
    cache,
    fetchedAssetCollections,
    isPending,
    retrieve,
    reset,
    deleteCacheKey,
    queueIdentifier,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAssetCacheStore, import.meta.hot));
