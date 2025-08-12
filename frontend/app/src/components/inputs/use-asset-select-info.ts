import type { AssetInfo } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import type { AssetMap } from '@/types/asset';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { getAssociatedAssetIdentifier, processAssetInfo, useAssetAssociationMap } from '@/composables/assets/common';
import { withRetry } from '@/services/with-retry';
import { chunkArray } from '@/utils/data';
import { logger } from '@/utils/logging';

interface AssetWithResolutionStatus extends AssetInfo {
  resolved: boolean;
}

interface UseAssetSelectInfoReturn {
  assetInfo: (identifier: MaybeRef<string | undefined>) => ComputedRef<AssetWithResolutionStatus | null>;
  assetSymbol: (identifier: MaybeRef<string | undefined>) => ComputedRef<string>;
  assetName: (identifier: MaybeRef<string | undefined>) => ComputedRef<string>;
}

export const useAssetSelectInfo = createSharedComposable((): UseAssetSelectInfoReturn => {
  const queuedAssets: Set<string> = new Set();
  const pendingAssets: Set<string> = new Set();
  const assetCache = ref<Record<string, AssetInfo | null>>({});
  const collectionCache = ref<Record<string, AssetInfo | null>>({});

  const { assetMapping } = useAssetInfoApi();
  const assetAssociationMap = useAssetAssociationMap();

  async function getAssetMapping(identifiers: string[]): Promise<AssetMap | undefined> {
    try {
      return await withRetry(async () => assetMapping(identifiers));
    }
    catch (error: any) {
      logger.error(error);
      return undefined;
    }
  }

  async function retrieveAssetInfo(identifiers: string[]): Promise<{ assets: Record<string, AssetInfo | null>; collections: Record<string, AssetInfo | null> }> {
    const assetInfoMap: Record<string, AssetInfo | null> = {};
    const collectionInfoMap: Record<string, AssetInfo | null> = {};
    const ids = identifiers.map(id => getAssociatedAssetIdentifier(id, get(assetAssociationMap)));

    for (const chunk of chunkArray(ids, 50)) {
      const mappings = await getAssetMapping(chunk);
      if (mappings === undefined) {
        continue;
      }
      const { assetCollections, assets } = mappings;

      for (const asset in assets) {
        assetInfoMap[asset] = assets[asset];
      }

      for (const collection in assetCollections) {
        collectionInfoMap[collection] = assetCollections[collection];
      }

      const foundIdentifiers = Object.keys(assets);
      const missingIdentifiers = chunk.filter(id => !foundIdentifiers.includes(id));

      for (const identifier of missingIdentifiers) {
        if (assetInfoMap[identifier] === undefined) {
          assetInfoMap[identifier] = null;
        }
      }
    }
    return { assets: assetInfoMap, collections: collectionInfoMap };
  }

  const processBatch = useDebounceFn(async () => {
    try {
      if (queuedAssets.size === 0) {
        return;
      }

      const assetsToProcess = Array.from(queuedAssets);
      queuedAssets.forEach(asset => pendingAssets.add(asset));
      queuedAssets.clear();

      logger.debug(`Processing batch of ${assetsToProcess.length} asset requests for AssetSelect`);

      const { assets, collections } = await retrieveAssetInfo(assetsToProcess);
      set(assetCache, {
        ...get(assetCache),
        ...assets,
      });
      set(collectionCache, {
        ...get(collectionCache),
        ...collections,
      });

      pendingAssets.clear();
    }
    catch (error: any) {
      logger.error('Error processing asset info batch for AssetSelect', error);
    }
  }, 1500);

  function getAssetInformation(assetId: string): void {
    const cache = get(assetCache);
    const key = getAssociatedAssetIdentifier(assetId, get(assetAssociationMap));
    if (cache[key] !== undefined || queuedAssets.has(key) || pendingAssets.has(key)) {
      return;
    }

    queuedAssets.add(key);
    processBatch()
      .then()
      .catch(error => logger.error(error));
  }

  const assetInfo = (
    identifier: MaybeRef<string | undefined>,
  ): ComputedRef<AssetWithResolutionStatus | null> => computed(() => {
    const id = get(identifier);
    if (!id)
      return null;

    const key = getAssociatedAssetIdentifier(id, get(assetAssociationMap));
    getAssetInformation(key);

    const cache = get(assetCache);
    const data = cache[key];

    if (!data) {
      return null;
    }

    const collectionData = data.collectionId ? get(collectionCache)[data.collectionId] : null;
    const processedInfo = processAssetInfo(data, id, collectionData);

    if (!processedInfo) {
      return null;
    }

    return {
      ...processedInfo,
      resolved: true,
    };
  });

  const assetSymbol = (
    identifier: MaybeRef<string | undefined>,
  ): ComputedRef<string> => computed(() => {
    const id = get(identifier);
    if (!id)
      return '';

    const info = get(assetInfo(id));
    return info?.symbol || '';
  });

  const assetName = (
    identifier: MaybeRef<string | undefined>,
  ): ComputedRef<string> => computed(() => {
    const id = get(identifier);
    if (!id)
      return '';

    const info = get(assetInfo(id));
    return info?.name || '';
  });

  return {
    assetInfo,
    assetName,
    assetSymbol,
  };
});
