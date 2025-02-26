import { useNotificationsStore } from '@/store/notifications';
import { useItemCache } from '@/composables/item-cache';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { logger } from '@/utils/logging';
import type { AssetCollection, AssetInfo } from '@rotki/common';
import type { AssetMap } from '@/types/asset';

export const useAssetCacheStore = defineStore('assets/cache', () => {
  const fetchedAssetCollections = ref<Record<string, AssetCollection>>({});

  const { assetMapping } = useAssetInfoApi();
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const getAssetMappingHandler = async (identifiers: string[]): Promise<AssetMap | undefined> => {
    try {
      return await assetMapping(identifiers);
    }
    catch (error: any) {
      logger.error(error);
      notify({
        display: true,
        message: t('asset_search.error.message', {
          message: error.message,
        }),
        title: t('asset_search.error.title'),
      });
      return undefined;
    }
  };

  const { cache, deleteCacheKey, isPending, queueIdentifier, reset, retrieve } = useItemCache<AssetInfo>(
    async (keys: string[]) => {
      const response = await getAssetMappingHandler(keys);
      return function* (): Generator<{ item: AssetInfo; key: string }, void> {
        if (!response)
          return;

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
    deleteCacheKey,
    fetchedAssetCollections,
    isPending,
    queueIdentifier,
    reset,
    retrieve,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAssetCacheStore, import.meta.hot));
