import type { AssetMap } from '@/types/asset';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useItemCache } from '@/composables/item-cache';
import { useNotificationsStore } from '@/store/notifications';
import { logger } from '@/utils/logging';
import { type AssetCollection, type AssetInfo, transformCase } from '@rotki/common';

export const useAssetCacheStore = defineStore('assets/cache', () => {
  const fetchedAssetCollections = ref<Record<string, AssetCollection>>({});

  const { assetMapping } = useAssetInfoApi();
  const { t } = useI18n({ useScope: 'global' });
  const { notify } = useNotificationsStore();

  const getAssetMappingHandler = async (identifiers: string[]): Promise<AssetMap | undefined> => {
    try {
      return await assetMapping(identifiers);
    }
    catch (error: any) {
      logger.error(error);
      notify({
        display: true,
        message: t('asset_mappings.error.message', {
          identifiers: identifiers.join(', '),
          message: error.message,
        }),
        title: t('asset_mappings.error.title'),
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
    getAssetMappingHandler,
    isPending,
    queueIdentifier,
    reset,
    retrieve,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAssetCacheStore, import.meta.hot));
