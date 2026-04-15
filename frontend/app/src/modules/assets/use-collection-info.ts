import type { ComputedRef, MaybeRef } from 'vue';
import type { AssetMap } from '@/modules/assets/types';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useResolveAssetIdentifier } from '@/composables/assets/common';
import { useCollectionMappingStore } from '@/modules/assets/use-collection-mapping-store';
import { chunkArray } from '@/utils/data';
import { logger } from '@/utils/logging';

interface CollectionInfo {
  assetToCollection: Record<string, string | null>;
  collectionMainAsset: Record<string, string | null>;
}

interface UseCollectionInfoReturn {
  getCollectionId: (assetId: string) => string | undefined;
  getCollectionMainAsset: (collectionId: string) => string | undefined;
  useCollectionId: (assetId: MaybeRef<string>) => ComputedRef<string | undefined>;
  useCollectionMainAsset: (collectionId: MaybeRef<string>) => ComputedRef<string | undefined>;
}

export const useCollectionInfo = createSharedComposable((): UseCollectionInfoReturn => {
  const queuedAssets: Set<string> = new Set();
  const pendingAssets: Set<string> = new Set();

  const { assetToCollection, collectionMainAsset } = storeToRefs(useCollectionMappingStore());
  const resolveAssetIdentifier = useResolveAssetIdentifier();
  const { assetMapping } = useAssetInfoApi();

  async function getAssetMapping(identifiers: string[]): Promise<AssetMap | undefined> {
    try {
      return await assetMapping(identifiers);
    }
    catch (error: unknown) {
      logger.error(error);
      return undefined;
    }
  }

  async function retrieveCollectionId(identifiers: string[]): Promise<CollectionInfo> {
    const assetToCollection: Record<string, string | null> = {};
    const collectionMainAsset: Record<string, string | null> = {};
    const ids = identifiers.map(id => resolveAssetIdentifier(id));
    for (const chunk of chunkArray(ids, 50)) {
      const mappings = await getAssetMapping(chunk);
      if (mappings === undefined) {
        continue;
      }
      const { assetCollections, assets } = mappings;

      for (const asset in assets) {
        assetToCollection[asset] = assets[asset].collectionId ?? null;
      }

      for (const collection in assetCollections) {
        collectionMainAsset[collection] = assetCollections[collection].mainAsset ?? null;
      }

      const foundIdentifiers = Object.keys(assets);
      const identifiers = [...chunk];
      const missingIdentifiers = identifiers.filter(id => !foundIdentifiers.includes(id));

      for (const identifier of missingIdentifiers) {
        if (assetToCollection[identifier] === undefined) {
          assetToCollection[identifier] = null;
        }
      }
    }
    return { assetToCollection, collectionMainAsset };
  }

  const processBatch = useDebounceFn(async () => {
    try {
      if (queuedAssets.size === 0) {
        return;
      }

      const assetsToProcess = Array.from(queuedAssets);
      queuedAssets.forEach(asset => pendingAssets.add(asset));
      queuedAssets.clear();

      logger.debug(`Processing batch of ${assetsToProcess.length} asset requests`);

      const collectionInfo = await retrieveCollectionId(assetsToProcess);
      set(assetToCollection, {
        ...get(assetToCollection),
        ...collectionInfo.assetToCollection,
      });
      set(collectionMainAsset, {
        ...get(collectionMainAsset),
        ...collectionInfo.collectionMainAsset,
      });

      pendingAssets.clear();
    }
    catch (error: unknown) {
      logger.error('Error processing asset collection batch', error);
    }
  }, 1500);

  function getCollectionInformation(assetId: string): void {
    const mapping = get(assetToCollection);
    if (mapping[assetId] !== undefined || queuedAssets.has(assetId) || pendingAssets.has(assetId)) {
      return;
    }

    queuedAssets.add(assetId);
    processBatch()
      .then()
      .catch(error => logger.error(error));
  }

  function getCollectionId(assetId: string): string | undefined {
    getCollectionInformation(assetId);
    return get(assetToCollection)[assetId];
  }

  function getCollectionMainAsset(collectionId: string): string | undefined {
    return get(collectionMainAsset)[collectionId] ?? undefined;
  }

  function useCollectionId(assetId: MaybeRef<string>): ComputedRef<string | undefined> {
    return computed<string | undefined>(() => getCollectionId(get(assetId)));
  }

  function useCollectionMainAsset(collectionId: MaybeRef<string>): ComputedRef<string | undefined> {
    return computed<string | undefined>(() => getCollectionMainAsset(get(collectionId)));
  }

  return {
    getCollectionId,
    getCollectionMainAsset,
    useCollectionId,
    useCollectionMainAsset,
  };
});
