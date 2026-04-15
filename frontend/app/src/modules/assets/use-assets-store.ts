import type { MaybeRefOrGetter } from 'vue';
import { useAssetIconApi } from '@/composables/api/assets/icon';
import { isBlockchain } from '@/modules/onchain/chains';

interface CachedAssetResult {
  exists: boolean;
  timestamp: number;
}

export const useAssetsStore = defineStore('assets', () => {
  // State
  const ignoredAssets = shallowRef<string[]>([]);
  const whitelistedAssets = shallowRef<string[]>([]);
  const lastRefreshedAssetIcon = ref<number>(0);
  const assetExistsCache = shallowRef<Map<string, CachedAssetResult>>(new Map());
  const pendingIconRequests = shallowRef<Map<string, Promise<boolean>>>(new Map());

  // Composables
  const { assetImageUrl } = useAssetIconApi();

  // Functions
  function isAssetIgnored(asset: string): boolean {
    return get(ignoredAssets).includes(asset);
  }

  function addIgnoredAsset(asset: string): void {
    const ignored = get(ignoredAssets);
    if (!ignored.includes(asset))
      set(ignoredAssets, [...ignored, asset]);
  }

  function isAssetWhitelisted(asset: string): boolean {
    return get(whitelistedAssets).includes(asset);
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

  // Computed factories
  function useIsAssetIgnored(asset: MaybeRefOrGetter<string>): ComputedRef<boolean> {
    return computed<boolean>(() => isAssetIgnored(toValue(asset)));
  }

  function useIsAssetWhitelisted(asset: MaybeRefOrGetter<string>): ComputedRef<boolean> {
    return computed<boolean>(() => isAssetWhitelisted(toValue(asset)));
  }

  // Watchers
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
