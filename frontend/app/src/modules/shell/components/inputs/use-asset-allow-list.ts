import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { AssetMap } from '@/modules/assets/types';
import { type AssetInfoWithId, transformCase } from '@rotki/common';
import { chunk } from 'es-toolkit';
import { useAssetInfoApi } from '@/modules/assets/api/use-asset-info-api';
import { mapWithConcurrency, MAX_PARALLEL_ASSET_BATCHES } from '@/modules/assets/use-asset-select-info';

/** How many identifiers go into one mapping request. */
const MAPPING_BATCH_SIZE = 50;

/**
 * How many assets the list offers before anything is typed. An owned list can run to thousands,
 * so the top of the caller's ranking is offered and typing reaches the rest.
 */
const OPEN_LIST_SIZE = 20;

interface UseAssetAllowListReturn {
  /** Whether an allow-list is set. An empty list means no restriction. */
  restricted: ComputedRef<boolean>;
  loading: Readonly<Ref<boolean>>;
  error: Readonly<Ref<string>>;
  /**
   * The allow-listed assets, in the order the caller gave them, that match `keyword` by symbol,
   * name or identifier; with no keyword, the first {@link OPEN_LIST_SIZE}. `keep` stays in
   * whatever the keyword.
   */
  filterAllowed: (keyword: string, keep?: string) => AssetInfoWithId[];
}

function toAssets(batch: string[], mapping: AssetMap): AssetInfoWithId[] {
  return batch.map(identifier => ({
    identifier,
    ...mapping.assets[transformCase(identifier, true)],
  }));
}

function matches(asset: AssetInfoWithId, keyword: string): boolean {
  return [asset.symbol, asset.name, asset.identifier].some(field => !!field && field.toLocaleLowerCase().includes(keyword));
}

/**
 * Turns an allow-list of identifiers into a closed option list for the asset picker.
 *
 * A remote search cannot serve an allow-list: it ranks the whole asset database and returns a page
 * of it, so a short query fills the page with assets outside the list and pushes listed ones off
 * it. Resolving the list itself and filtering locally keeps every listed asset reachable.
 */
export function useAssetAllowList(items: MaybeRefOrGetter<string[] | undefined>): UseAssetAllowListReturn {
  const { assetMapping } = useAssetInfoApi();

  const allowedAssets = shallowRef<AssetInfoWithId[]>([]);
  const loading = shallowRef<boolean>(false);
  const error = shallowRef<string>('');
  let request = 0;

  const allowList = computed<string[]>(() => toValue(items) ?? []);
  const restricted = computed<boolean>(() => get(allowList).length > 0);

  /** The list's contents: callers pass a fresh array on every re-render, which must not re-resolve. */
  const allowListKey = computed<string>(() => get(allowList).join('\n'));

  /**
   * The first batch resolves alone and is published straight away, since it holds the top of the
   * list the picker opens on; the rest follow with a capped number of requests in flight.
   */
  async function resolve(identifiers: string[]): Promise<void> {
    const current = ++request;
    set(error, '');

    if (identifiers.length === 0) {
      set(allowedAssets, []);
      set(loading, false);
      return;
    }

    set(loading, true);
    try {
      const [first, ...others] = chunk(identifiers, MAPPING_BATCH_SIZE);
      const head = toAssets(first, await assetMapping(first));
      // A newer list replaced this one while it was resolving.
      if (current !== request)
        return;

      set(allowedAssets, head);

      const tail = await mapWithConcurrency(
        others,
        MAX_PARALLEL_ASSET_BATCHES,
        async batch => toAssets(batch, await assetMapping(batch)),
      );
      if (current !== request)
        return;

      set(allowedAssets, [...head, ...tail.flat()]);
    }
    catch (error_: any) {
      if (current === request)
        set(error, error_.message);
    }
    finally {
      if (current === request)
        set(loading, false);
    }
  }

  function filterAllowed(keyword: string, keep?: string): AssetInfoWithId[] {
    const search = keyword.trim().toLocaleLowerCase();
    const assets = get(allowedAssets);
    if (!search) {
      const top = assets.slice(0, OPEN_LIST_SIZE);
      const selected = keep && !top.some(asset => asset.identifier === keep)
        ? assets.find(asset => asset.identifier === keep)
        : undefined;
      return selected ? [...top, selected] : top;
    }

    return assets.filter(asset => asset.identifier === keep || matches(asset, search));
  }

  watch(allowListKey, async () => {
    await resolve(get(allowList));
  }, { immediate: true });

  return {
    error: readonly(error),
    filterAllowed,
    loading: readonly(loading),
    restricted,
  };
}
