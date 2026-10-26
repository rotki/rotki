import type { MaybeRefOrGetter } from 'vue';
import { useAssetIconApi } from '@/modules/assets/api/use-asset-icon-api';
import { isBlockchain } from '@/modules/core/common/chains';

interface CachedAssetResult {
  exists: boolean;
  timestamp: number;
}

export const useAssetsStore = defineStore('assets', () => {
  const ignoredAssets = shallowRef<string[]>([]);
  const whitelistedAssets = shallowRef<string[]>([]);
  const lastRefreshedAssetIcon = ref<number>(0);
  const assetExistsCache = shallowRef<Map<string, CachedAssetResult>>(new Map());
  const pendingIconRequests = shallowRef<Map<string, Promise<boolean>>>(new Map());

  const { assetImageUrl } = useAssetIconApi();

  /**
   * The ignored assets as a set, rebuilt only when the list changes.
   *
   * @remarks
   * Balance aggregation asks once per asset on every pass, and the list holds the whole spam list,
   * thousands of entries, so every membership check goes through this set rather than the list.
   */
  const ignoredAssetSet = computed<Set<string>>(() => new Set(get(ignoredAssets)));

  /** The whitelisted assets as a set, for the same reason as {@link ignoredAssetSet}. */
  const whitelistedAssetSet = computed<Set<string>>(() => new Set(get(whitelistedAssets)));

  function isAssetIgnored(asset: string): boolean {
    return get(ignoredAssetSet).has(asset);
  }

  function addIgnoredAsset(asset: string): void {
    if (!isAssetIgnored(asset))
      set(ignoredAssets, [...get(ignoredAssets), asset]);
  }

  function isAssetWhitelisted(asset: string): boolean {
    return get(whitelistedAssetSet).has(asset);
  }

  function setLastRefreshedAssetIcon(): void {
    set(lastRefreshedAssetIcon, Date.now());
  }

  function clearIconCache(): void {
    get(assetExistsCache).clear();
    get(pendingIconRequests).clear();
  }

  function getAssetIconUrl(identifier: string): string {
    const id = isBlockchain(identifier) ? identifier.toUpperCase() : identifier;
    return assetImageUrl(id, get(lastRefreshedAssetIcon));
  }

  function useIsAssetIgnored(asset: MaybeRefOrGetter<string>): ComputedRef<boolean> {
    return computed<boolean>(() => isAssetIgnored(toValue(asset)));
  }

  function useIsAssetWhitelisted(asset: MaybeRefOrGetter<string>): ComputedRef<boolean> {
    return computed<boolean>(() => isAssetWhitelisted(toValue(asset)));
  }

  watch(lastRefreshedAssetIcon, () => {
    clearIconCache();
  });

  return {
    addIgnoredAsset,
    assetExistsCache,
    clearIconCache,
    getAssetIconUrl,
    ignoredAssets,
    isAssetIgnored,
    isAssetWhitelisted,
    lastRefreshedAssetIcon,
    pendingIconRequests,
    setLastRefreshedAssetIcon,
    useIsAssetIgnored,
    useIsAssetWhitelisted,
    whitelistedAssets,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAssetsStore, import.meta.hot));
