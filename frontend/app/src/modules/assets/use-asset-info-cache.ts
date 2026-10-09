import type { ShallowRef } from 'vue';
import type { AssetMap } from '@/modules/assets/types';
import { type AssetCollection, type AssetInfo, NotificationGroup, Priority, Severity, transformCase } from '@rotki/common';
import { useAssetInfoApi } from '@/modules/assets/api/use-asset-info-api';
import { useAssetInfoCacheStore } from '@/modules/assets/use-asset-info-cache-store';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { createItemCache } from '@/modules/core/common/use-item-cache';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

/** A batch can hold hundreds of identifiers; the notification names the first few. */
const MAX_LISTED_IDENTIFIERS = 5;

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
  const assetInfoCacheStore = useAssetInfoCacheStore();
  const { storage } = assetInfoCacheStore;
  const { fetchedAssetCollections } = storeToRefs(assetInfoCacheStore);

  const { assetMapping } = useAssetInfoApi();
  const { t } = useI18n({ useScope: 'global' });
  const { notify } = useNotifications();

  /** Failed lookups so far; every failure updates one grouped notification instead of adding another. */
  let failures = 0;

  function describeIdentifiers(identifiers: string[]): string {
    const shown = identifiers.slice(0, MAX_LISTED_IDENTIFIERS).join(', ');
    const hidden = identifiers.length - MAX_LISTED_IDENTIFIERS;
    return hidden > 0 ? t('asset_mappings.error.identifiers_more', { count: hidden, identifiers: shown }) : shown;
  }

  function notifyFailure(identifiers: string[], error: unknown): void {
    logger.error(error);
    failures += 1;
    notify({
      group: NotificationGroup.ASSET_MAPPINGS,
      groupCount: failures,
      message: t(
        'asset_mappings.error.message',
        {
          count: failures,
          identifiers: describeIdentifiers(identifiers),
          message: getErrorMessage(error),
        },
        failures,
      ),
      priority: Priority.NORMAL,
      severity: Severity.ERROR,
      title: t('asset_mappings.error.title'),
    });
  }

  const getAssetMappingHandler = async (identifiers: string[]): Promise<AssetMap | undefined> => {
    try {
      return await assetMapping(identifiers);
    }
    catch (error: unknown) {
      notifyFailure(identifiers, error);
      return undefined;
    }
  };

  /** The cache's fetch rethrows a failure, so the cache backs the keys off and gives up after a few tries. */
  const fetchForCache = async (identifiers: string[]): Promise<AssetMap> => {
    try {
      return await assetMapping(identifiers);
    }
    catch (error: unknown) {
      notifyFailure(identifiers, error);
      throw error;
    }
  };

  const { cache, deleteCacheKey, isPending, queueIdentifier, reset, resolve } = createItemCache<AssetInfo>(
    async (keys: string[]) => {
      const response = await fetchForCache(keys);
      return function* (): Generator<{ item: AssetInfo; key: string }, void> {
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
      label: 'asset-info',
      maxSize: 5000,
      size: 500,
      storage,
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
