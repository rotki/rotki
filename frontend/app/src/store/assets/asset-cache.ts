import type { AssetMap } from '@/types/asset';
import { type AssetCollection, type AssetInfo, transformCase } from '@rotki/common';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useItemCache } from '@/composables/item-cache';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { getErrorMessage } from '@/utils/error-handling';
import { logger } from '@/utils/logging';

export const useAssetCacheStore = defineStore('assets/cache', () => {
  const fetchedAssetCollections = ref<Record<string, AssetCollection>>({});

  const { assetMapping } = useAssetInfoApi();
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();

  const getAssetMappingHandler = async (identifiers: string[]): Promise<AssetMap | undefined> => {
    try {
      return await assetMapping(identifiers);
    }
    catch (error: unknown) {
      logger.error(error);
      notifyError(
        t('asset_mappings.error.title'),
        t('asset_mappings.error.message', {
          identifiers: identifiers.join(', '),
          message: getErrorMessage(error),
        }),
      );
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
    {
      debounceInMs: 100,
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
