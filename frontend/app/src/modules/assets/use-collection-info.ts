import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import type { AssetMap } from '@/types/asset';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useCollectionMappingStore } from '@/modules/assets/use-collection-mapping-store';
import { chunkArray } from '@/utils/data';
import { logger } from '@/utils/logging';

interface CollectionInfo {
  assetToCollection: Record<string, string | null>;
  collectionMainAsset: Record<string, string | null>;
}

interface UseCollectionInfoReturn {
  useCollectionId: (assetId: MaybeRef<string>) => ComputedRef<string | undefined>;
  useCollectionMainAsset: (collectionId: MaybeRef<string>) => ComputedRef<string | undefined>;
}

export const useCollectionInfo = createSharedComposable((): UseCollectionInfoReturn => {
  const queuedAssets: Set<string> = new Set();
  const pendingAssets: Set<string> = new Set();

  const { assetAssociationMap } = useAssetInfoRetrieval();
  const { assetToCollection, collectionMainAsset } = storeToRefs(useCollectionMappingStore());

  const { assetMapping } = useAssetInfoApi();

  async function getAssetMapping(identifiers: string[]): Promise<AssetMap | undefined> {
    try {
      return await assetMapping(identifiers);
    }
    catch (error: any) {
      logger.error(error);
      return undefined;
    }
  }

  async function retrieveCollectionId(identifiers: string[]): Promise<CollectionInfo> {
    const assetToCollection: Record<string, string | null> = {};
    const collectionMainAsset: Record<string, string | null> = {};
    const ids = identifiers.map(id => get(assetAssociationMap)[id] ?? id);
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
    catch (error: any) {
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

  function useCollectionId(assetId: MaybeRef<string>): ComputedRef<string | undefined> {
    return computed(() => {
      const identifier = get(assetId);
      getCollectionInformation(identifier);
      const mapping = get(assetToCollection);
      return mapping[identifier];
    });
  }

  function useCollectionMainAsset(collectionId: MaybeRef<string>): ComputedRef<string | undefined> {
    return computed(() => {
      const identifier = get(collectionId);
      const mapping = get(collectionMainAsset);
      return mapping[identifier] ?? undefined;
    });
  }

  return {
    useCollectionId,
    useCollectionMainAsset,
  };
});
