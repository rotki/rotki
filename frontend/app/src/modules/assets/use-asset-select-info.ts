import type { AssetInfo } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { AssetMap } from '@/modules/assets/types';
import type { AssetStringField } from '@/modules/assets/use-asset-info-retrieval';
import { startPromise } from '@shared/utils';
import { chunk } from 'es-toolkit';
import { useAssetInfoApi } from '@/modules/assets/api/use-asset-info-api';
import { processAssetInfo, useResolveAssetIdentifier } from '@/modules/assets/use-resolve-asset-identifier';
import { logger } from '@/modules/core/common/logging/logging';

interface AssetWithResolutionStatus extends AssetInfo {
  resolved: boolean;
}

type PlainAssetInfoReturn = (identifier: string | undefined) => AssetWithResolutionStatus | null;

interface UseAssetSelectInfoReturn {
  getAssetField: (identifier: string | undefined, field: AssetStringField) => string;
  getAssetInfo: PlainAssetInfoReturn;
  prefetchAssetInfo: (identifiers: string[]) => void;
  useAssetField: (identifier: MaybeRefOrGetter<string | undefined>, field: AssetStringField) => ComputedRef<string>;
  useAssetInfo: (identifier: MaybeRefOrGetter<string | undefined>) => ComputedRef<AssetWithResolutionStatus | null>;
}

/**
 * How long queued identifiers are collected before a batch is sent.
 *
 * @remarks
 * This coalesces the burst a list emits while it renders, so it only has to outlast one render
 * pass. Raising it much is worse than it looks: an unresolved asset has no name or symbol to match
 * on, so until the batch returns a cold cache filters every row out, and the user reads an empty
 * table while the first request has yet to leave.
 */
const BATCH_DEBOUNCE_MS = 200;

/** How many mapping requests may be in flight at once for one batch of queued identifiers. */
export const MAX_PARALLEL_ASSET_BATCHES = 4;

/**
 * Like `items.map(fn)` awaited together, but with at most `limit` calls outstanding.
 *
 * Results keep the order of the input regardless of the order they complete in.
 */
async function mapWithConcurrency<T, R>(items: T[], limit: number, fn: (item: T) => Promise<R>): Promise<R[]> {
  const results: R[] = Array.from({ length: items.length });
  let next = 0;

  async function worker(): Promise<void> {
    while (next < items.length) {
      const index = next++;
      results[index] = await fn(items[index]);
    }
  }

  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, async () => worker()));
  return results;
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

    // The batches are independent, so several are in flight at once: awaiting them one after the
    // other made a large balance list wait for one round trip per 50 assets before the search could
    // match anything. They are capped rather than all released together, because a large portfolio
    // is 20 batches, more than one table prefetches its own list, and the backend serving them is a
    // single local process.
    const batches = chunk(ids, 50);
    const responses = await mapWithConcurrency(
      batches,
      MAX_PARALLEL_ASSET_BATCHES,
      async batch => ({ batch, mappings: await getAssetMapping(batch) }),
    );

    for (const { batch, mappings } of responses) {
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

      const foundIdentifiers = new Set(Object.keys(assets));

      for (const identifier of batch) {
        if (!foundIdentifiers.has(identifier) && assetInfoMap[identifier] === undefined) {
          assetInfoMap[identifier] = null;
        }
      }
    }
    return { assets: assetInfoMap, collections: collectionInfoMap };
  }

  const processBatch = useDebounceFn(async () => {
    if (queuedAssets.size === 0) {
      return;
    }

    const assetsToProcess = Array.from(queuedAssets);
    queuedAssets.forEach(asset => pendingAssets.add(asset));
    queuedAssets.clear();

    try {
      logger.debug(`Processing batch of ${assetsToProcess.length} asset requests for AssetSelect`);

      const { assets, collections } = await retrieveAssetInfo(assetsToProcess);

      if (Object.keys(assets).length > 0)
        set(assetCache, Object.assign({}, get(assetCache), assets));

      if (Object.keys(collections).length > 0)
        set(collectionCache, Object.assign({}, get(collectionCache), collections));
    }
    catch (error: unknown) {
      logger.error('Error processing asset info batch for AssetSelect', error);
    }
    finally {
      // Only this batch is released. Clearing the whole set would let a concurrent batch's
      // identifiers be queued a second time while their request is still in flight.
      assetsToProcess.forEach(asset => pendingAssets.delete(asset));
    }
  }, BATCH_DEBOUNCE_MS);

  function queueAssetInformation(key: string): boolean {
    const cache = get(assetCache);
    if (cache[key] !== undefined || queuedAssets.has(key) || pendingAssets.has(key)) {
      return false;
    }

    queuedAssets.add(key);
    return true;
  }

  function queueAndProcess(key: string): void {
    if (queueAssetInformation(key)) {
      startPromise(processBatch());
    }
  }

  /**
   * Warms the cache for a known set of identifiers in one batch.
   *
   * Resolution is otherwise driven by rendering, so an identifier that is in a list but not on the
   * visible page stays unresolved. Anything reading the whole list (a search, a sort by name) needs
   * every entry resolved, and discovering that only once the user types costs a full round trip
   * with the result on screen already reading "no results".
   */
  function prefetchAssetInfo(identifiers: string[]): void {
    let queued = false;
    for (const identifier of identifiers) {
      if (!identifier) {
        continue;
      }
      queued = queueAssetInformation(resolveAssetIdentifier(identifier)) || queued;
    }

    if (queued) {
      startPromise(processBatch());
    }
  }

  const getAssetInfo: PlainAssetInfoReturn = (
    identifier: string | undefined,
  ): AssetWithResolutionStatus | null => {
    if (!identifier)
      return null;

    const key = resolveAssetIdentifier(identifier);
    queueAndProcess(key);

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
    prefetchAssetInfo,
    useAssetField,
    useAssetInfo,
  };
});
