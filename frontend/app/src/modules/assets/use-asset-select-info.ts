import type { AssetInfo } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { AssetMap } from '@/modules/assets/types';
import type { AssetStringField } from '@/modules/assets/use-asset-info-retrieval';
import { startPromise } from '@shared/utils';
import { useAssetInfoApi } from '@/modules/assets/api/use-asset-info-api';
import { processAssetInfo, useResolveAssetIdentifier } from '@/modules/assets/use-resolve-asset-identifier';
import { chunkArray } from '@/modules/core/common/data/data';
import { logger } from '@/modules/core/common/logging/logging';

interface AssetWithResolutionStatus extends AssetInfo {
  resolved: boolean;
}

type PlainAssetInfoReturn = (identifier: string | undefined) => AssetWithResolutionStatus | null;

interface UseAssetSelectInfoReturn {
  getAssetField: (identifier: string | undefined, field: AssetStringField) => string;
  getAssetInfo: PlainAssetInfoReturn;
  useAssetField: (identifier: MaybeRefOrGetter<string | undefined>, field: AssetStringField) => ComputedRef<string>;
  useAssetInfo: (identifier: MaybeRefOrGetter<string | undefined>) => ComputedRef<AssetWithResolutionStatus | null>;
}

export const useAssetSelectInfo = createSharedComposable((): UseAssetSelectInfoReturn => {
  const queuedAssets: Set<string> = new Set();
  const pendingAssets: Set<string> = new Set();
  const assetCache = shallowRef<Record<string, AssetInfo | null>>({});
  const collectionCache = shallowRef<Record<string, AssetInfo | null>>({});

  const { assetMapping } = useAssetInfoApi();
  const resolveAssetIdentifier = useResolveAssetIdentifier();

  async function getAssetMapping(identifiers: string[]): Promise<AssetMap | undefined> {
    try {
      return await assetMapping(identifiers);
    }
    catch (error: unknown) {
      logger.error(error);
      return undefined;
    }
  }

  async function retrieveAssetInfo(identifiers: string[]): Promise<{ assets: Record<string, AssetInfo | null>; collections: Record<string, AssetInfo | null> }> {
    const assetInfoMap: Record<string, AssetInfo | null> = {};
    const collectionInfoMap: Record<string, AssetInfo | null> = {};
    const ids = identifiers.map(id => resolveAssetIdentifier(id));

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
      set(assetCache, Object.assign({}, get(assetCache), assets));
      set(collectionCache, Object.assign({}, get(collectionCache), collections));

      pendingAssets.clear();
    }
    catch (error: unknown) {
      logger.error('Error processing asset info batch for AssetSelect', error);
    }
  }, 1500);

  function queueAssetInformation(key: string): void {
    const cache = get(assetCache);
    if (cache[key] !== undefined || queuedAssets.has(key) || pendingAssets.has(key)) {
      return;
    }

    queuedAssets.add(key);
    startPromise(processBatch());
  }

  const getAssetInfo: PlainAssetInfoReturn = (
    identifier: string | undefined,
  ): AssetWithResolutionStatus | null => {
    if (!identifier)
      return null;

    const key = resolveAssetIdentifier(identifier);
    queueAssetInformation(key);

    const cache = get(assetCache);
    const data = cache[key];

    if (!data) {
      return null;
    }

    const collectionData = data.collectionId ? get(collectionCache)[data.collectionId] : null;
    const processedInfo = processAssetInfo(data, identifier, collectionData);

    if (!processedInfo) {
      return null;
    }

    return {
      ...processedInfo,
      resolved: true,
    };
  };

  const useAssetInfo = (
    identifier: MaybeRefOrGetter<string | undefined>,
  ): ComputedRef<AssetWithResolutionStatus | null> =>
    computed<AssetWithResolutionStatus | null>(() => getAssetInfo(toValue(identifier)));

  const getAssetField = (
    identifier: string | undefined,
    field: AssetStringField,
  ): string => {
    if (!identifier)
      return '';
    return getAssetInfo(identifier)?.[field] ?? '';
  };

  const useAssetField = (
    identifier: MaybeRefOrGetter<string | undefined>,
    field: AssetStringField,
  ): ComputedRef<string> =>
    computed<string>(() => getAssetField(toValue(identifier), field));

  return {
    getAssetField,
    getAssetInfo,
    useAssetField,
    useAssetInfo,
  };
});
