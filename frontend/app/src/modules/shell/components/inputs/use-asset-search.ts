import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { NftAsset } from '@/modules/assets/nfts';
import { assert, type AssetInfoWithId, transformCase } from '@rotki/common';
import { useAssetInfoApi } from '@/modules/assets/api/use-asset-info-api';
import { NftHandling } from '@/modules/assets/nft-handling';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { uniqueObjects } from '@/modules/core/common/data/data';
import { getAssetSearchTypeParams, getSanitizedChain, parseAssetSearchKeyword } from '@/modules/core/common/display/assets';
import { isAbortError } from '@/modules/core/common/helpers/is-of-enum';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

type Asset = AssetInfoWithId | NftAsset;

/**
 * Which assets a picker may offer: the allow-list, the exclusions, the chain it is scoped to, and
 * how ignored assets and NFTs are treated.
 *
 * One object rather than five arguments because they are one decision — what the user may pick —
 * and because `AssetSelect` passes them straight through, where five separate props pushed it past
 * the lint ceiling on a component that is part of the premium bundle's API.
 */
export interface AssetSearchSource {
  /** Restricts the options to this allow-list of identifiers. */
  items?: string[];
  /** Removes these identifiers from the options. */
  excludes?: string[];
  /** Scopes the remote search to a chain. */
  chain?: string;
  /** When true, ignored assets stay in the options. */
  showIgnored?: boolean;
  /** Whether NFTs are left out of the search, searched alongside the assets, or searched alone. */
  nfts?: NftHandling;
}

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
  /** Whether NFTs are left out of the search, searched alongside the assets, or searched alone. */
  nftHandling?: MaybeRefOrGetter<NftHandling>;
  /**
   * Called when a selection that *was* in the options drops out of them, e.g. after the chain
   * scope changes under it. The caller decides what to do about it, since only it knows what else
   * hangs off the selection.
   */
  onSelectionLost?: () => void;
}

interface UseAssetSearchReturn {
  modelSearch: Ref<string>;
  loading: Readonly<Ref<boolean>>;
  error: Readonly<Ref<string>>;
  visibleAssets: ComputedRef<AssetInfoWithId[]>;
  getVisibleAsset: (identifier: string) => AssetInfoWithId | undefined;
  /** Fills the options from a search without prefilling the search box. See below. */
  preload: (keyword: string) => Promise<void>;
}

/**
 * Owns the asset search for the asset picker: the debounced, chain-scoped remote search, the
 * cached option list and its ignored/items/excludes filtering, and keeping the selected value in
 * the options. Kept UI-free so the search/filter behaviour can be tested without mounting the
 * autocomplete.
 */
export function useAssetSearch(options: UseAssetSearchOptions): UseAssetSearchReturn {
  const { chain, excludes, items, modelValue, nftHandling, onSelectionLost, showIgnored } = options;

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

  async function resolveSelected(): Promise<Asset | undefined> {
    const val = get(modelValue);
    assert(val);
    const mapping = await assetMapping([val]);
    return {
      identifier: val,
      ...mapping.assets[transformCase(val, true)],
    };
  }

  /** Replaces the options with `newAssets`, with the selected value appended so it is never absent. */
  async function retainSelectedValueInOptions(newAssets: Asset[]): Promise<void> {
    try {
      const selectedAsset = await resolveSelected();
      if (selectedAsset)
        set(assets, [...newAssets, selectedAsset]);
    }
    catch (error_: any) {
      set(loading, false);
      set(error, error_.message);
    }
  }

  /**
   * Adds the selected value to whatever the options hold, without replacing them.
   *
   * The list is read *after* the mapping request resolves, not captured before it. That is the
   * difference that matters: this runs on mount at the same time as an opening search, and a
   * snapshot taken up front would wipe whichever of the two resolved first, leaving a list of one.
   */
  async function addSelectedToOptions(): Promise<void> {
    try {
      const selectedAsset = await resolveSelected();
      if (!selectedAsset)
        return;

      set(assets, uniqueObjects<Asset>(
        [...get(assets).filter(item => item.identifier !== selectedAsset.identifier), selectedAsset],
        item => item.identifier,
      ));
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
        nftHandling: toValue(nftHandling) ?? NftHandling.EXCLUDE,
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

    await addSelectedToOptions();
  }

  watch(modelValue, async () => {
    await checkValue();
  });

  /**
   * Only a selection that was visible and then stopped being visible counts as lost. A value that
   * was never in the options is a freshly picked one whose mapping has not arrived yet, and
   * clearing on that would undo the user's own selection a moment after they made it.
   */
  watch(visibleAssets, (_, previous) => {
    const identifier = get(modelValue);
    if (!identifier || !previous)
      return;

    if (!previous.some(asset => asset.identifier === identifier))
      return;

    if (!getVisibleAsset(identifier))
      onSelectionLost?.();
  });

  watch(modelSearch, (value) => {
    if (value)
      set(loading, true);
    else if (!pending)
      set(loading, false);
  });

  async function runSearch(keyword: string): Promise<void> {
    if (pending) {
      pending.abort();
      pending = null;
    }
    set(error, '');
    pending = new AbortController();
    await searchAssets(keyword, pending.signal);
  }

  watchDebounced(modelSearch, async (value) => {
    if (!value)
      return set(loading, false);

    await runSearch(value);
  }, { debounce: 350 });

  watch(() => toValue(chain), async () => {
    if (!get(modelValue)) {
      // Drop options cached for the previous chain so a stale, off-chain asset can't be picked;
      // the next search repopulates for the new chain.
      set(assets, []);
      return;
    }
    await retainSelectedValueInOptions([]);
  });

  /**
   * Fills the options from a search without routing the keyword through `modelSearch`, so a
   * picker can open on a non-empty list while its search box stays empty. Writing the keyword to
   * `modelSearch` would show it as text the user has to clear before typing their own.
   *
   * Runs immediately, skipping the debounce the typed path uses.
   */
  async function preload(keyword: string): Promise<void> {
    await runSearch(keyword);
  }

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
    preload,
    visibleAssets,
  };
}
