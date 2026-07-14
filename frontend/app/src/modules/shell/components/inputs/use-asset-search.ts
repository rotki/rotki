import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { NftAsset } from '@/modules/assets/nfts';
import { assert, type AssetInfoWithId, transformCase } from '@rotki/common';
import { useAssetInfoApi } from '@/modules/assets/api/use-asset-info-api';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { uniqueObjects } from '@/modules/core/common/data/data';
import { getAssetSearchTypeParams, getSanitizedChain, parseAssetSearchKeyword } from '@/modules/core/common/display/assets';
import { isAbortError } from '@/modules/core/common/helpers/is-of-enum';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

type Asset = AssetInfoWithId | NftAsset;

interface UseAssetSearchOptions {
  /** The selected asset identifier; kept in the options and used to gate ignored-asset filtering. */
  modelValue: Ref<string | undefined>;
  /** Scopes the remote search to a chain and resets the cached options when it changes. */
  chain?: MaybeRefOrGetter<string | undefined>;
  /** When true, ignored assets stay in the options. */
  showIgnored?: MaybeRefOrGetter<boolean>;
  /** Restricts the options to this allow-list of identifiers. */
  items?: MaybeRefOrGetter<string[]>;
  /** Removes these identifiers from the options. */
  excludes?: MaybeRefOrGetter<string[]>;
  /** Includes NFTs in the search results. */
  includeNfts?: MaybeRefOrGetter<boolean>;
}

interface UseAssetSearchReturn {
  modelSearch: Ref<string>;
  loading: Readonly<Ref<boolean>>;
  error: Readonly<Ref<string>>;
  visibleAssets: ComputedRef<AssetInfoWithId[]>;
  getVisibleAsset: (identifier: string) => AssetInfoWithId | undefined;
}

/**
 * Owns the asset search for the asset picker: the debounced, chain-scoped remote search, the
 * cached option list and its ignored/items/excludes filtering, and keeping the selected value in
 * the options. Kept UI-free so the search/filter behaviour can be tested without mounting the
 * autocomplete.
 */
export function useAssetSearch(options: UseAssetSearchOptions): UseAssetSearchReturn {
  const { chain, excludes, includeNfts, items, modelValue, showIgnored } = options;

  const { isAssetIgnored } = useAssetsStore();
  const { getEvmChainName, matchChain } = useSupportedChains();
  const { assetMapping, assetSearch } = useAssetInfoApi();

  const modelSearch = shallowRef<string>('');
  const assets = ref<Asset[]>([]);
  const error = shallowRef<string>('');
  const loading = shallowRef<boolean>(false);
  let pending: AbortController | null = null;

  const visibleAssets = computed<AssetInfoWithId[]>(() => {
    const knownAssets = get(assets);
    const currentValue = get(modelValue);
    const ignoredVisible = toValue(showIgnored) ?? false;
    const includeList = toValue(items) ?? [];
    const excludeList = toValue(excludes) ?? [];

    const filtered = knownAssets.filter(({ identifier }: AssetInfoWithId) => {
      const isCurrentValue = identifier === currentValue;
      const unIgnored = ignoredVisible || isCurrentValue || !isAssetIgnored(identifier);
      const included = includeList.length > 0 ? includeList.includes(identifier) : true;
      const excluded = excludeList.length > 0
        ? excludeList.some(excludedId => identifier.toLowerCase() === excludedId?.toLowerCase())
        : false;

      return !!identifier && unIgnored && included && !excluded;
    });

    return uniqueObjects<AssetInfoWithId>(filtered, item => item.identifier);
  });

  function getVisibleAsset(identifier: string): AssetInfoWithId | undefined {
    return get(visibleAssets)?.find(asset => asset.identifier === identifier);
  }

  async function retainSelectedValueInOptions(newAssets: Asset[]): Promise<void> {
    try {
      const val = get(modelValue);
      assert(val);
      const mapping = await assetMapping([val]);
      set(assets, [
        ...newAssets,
        {
          identifier: val,
          ...mapping.assets[transformCase(val, true)],
        },
      ]);
    }
    catch (error_: any) {
      set(loading, false);
      set(error, error_.message);
    }
  }

  async function searchAssets(keyword: string, signal: AbortSignal): Promise<void> {
    set(loading, true);
    try {
      const { address, value } = parseAssetSearchKeyword(keyword);
      const usedChain = getSanitizedChain(toValue(chain), matchChain, getEvmChainName);

      const fetchedAssets = await assetSearch({
        address,
        ...getAssetSearchTypeParams(usedChain),
        limit: 50,
        searchNfts: toValue(includeNfts) ?? false,
        signal,
        value,
      });
      if (get(modelValue))
        await retainSelectedValueInOptions(fetchedAssets);
      else
        set(assets, fetchedAssets);

      pending = null;
      set(loading, false);
    }
    catch (error_: any) {
      if (!isAbortError(error_)) {
        set(loading, false);
        set(error, error_.message);
      }
    }
  }

  async function checkValue(): Promise<void> {
    if (!get(modelValue))
      return;

    await retainSelectedValueInOptions(get(assets));
  }

  watch(modelValue, async () => {
    await checkValue();
  });

  watch(modelSearch, (value) => {
    if (value)
      set(loading, true);
    else if (!pending)
      set(loading, false);
  });

  watchDebounced(modelSearch, async (value) => {
    if (!value)
      return set(loading, false);

    if (pending) {
      pending.abort();
      pending = null;
    }
    set(error, '');
    pending = new AbortController();
    await searchAssets(value, pending.signal);
  }, { debounce: 800 });

  watch(() => toValue(chain), async () => {
    if (!get(modelValue)) {
      // Drop options cached for the previous chain so a stale, off-chain asset can't be picked;
      // the next search repopulates for the new chain.
      set(assets, []);
      return;
    }
    await retainSelectedValueInOptions([]);
  });

  onMounted(async () => {
    await checkValue();
  });

  onUnmounted(() => {
    pending?.abort();
  });

  return {
    error: readonly(error),
    getVisibleAsset,
    loading: readonly(loading),
    modelSearch,
    visibleAssets,
  };
}
