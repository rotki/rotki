import type { ShallowRef } from 'vue';
import type { AssetMap } from '@/modules/assets/types';
import { type AssetCollection, type AssetInfo, transformCase } from '@rotki/common';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { createItemCache } from '@/composables/item-cache';
import { getErrorMessage } from '@/modules/common/logging/error-handling';
import { logger } from '@/modules/common/logging/logging';
import { useNotifications } from '@/modules/notifications/use-notifications';

interface UseAssetInfoCacheReturn {
  cache: ReturnType<typeof createItemCache<AssetInfo>>['cache'];
  deleteCacheKey: (key: string) => void;
  fetchedAssetCollections: ShallowRef<Record<string, AssetCollection>>;
  getAssetMappingHandler: (identifiers: string[]) => Promise<AssetMap | undefined>;
  isPending: ReturnType<typeof createItemCache<AssetInfo>>['isPending'];
  queueIdentifier: (key: string) => void;
  reset: () => void;
  resolve: (key: string) => AssetInfo | null;
}

export const useAssetInfoCache = createSharedComposable((): UseAssetInfoCacheReturn => {
  const fetchedAssetCollections = shallowRef<Record<string, AssetCollection>>({});

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

  const { cache, deleteCacheKey, isPending, queueIdentifier, reset, resolve } = createItemCache<AssetInfo>(
    async (keys: string[]) => {
      const response = await getAssetMappingHandler(keys);
      return function* (): Generator<{ item: AssetInfo; key: string }, void> {
        if (!response)
          return;

        const { assetCollections, assets } = response;
        if (Object.keys(assetCollections).length > 0) {
          set(fetchedAssetCollections, {
            ...get(fetchedAssetCollections),
            ...assetCollections,
          });
        }

        for (const key of keys) {
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
    resolve,
  };
});
