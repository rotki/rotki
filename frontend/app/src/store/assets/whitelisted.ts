import type { MaybeRefOrGetter } from 'vue';

export const useWhitelistedAssetsStore = defineStore('assets/whitelisted', () => {
  const whitelistedAssets = shallowRef<string[]>([]);

  function isAssetWhitelisted(asset: string): boolean {
    return get(whitelistedAssets).includes(asset);
  }

  function useIsAssetWhitelisted(asset: MaybeRefOrGetter<string>): ComputedRef<boolean> {
    return computed<boolean>(() => isAssetWhitelisted(toValue(asset)));
  }

  return {
    isAssetWhitelisted,
    useIsAssetWhitelisted,
    whitelistedAssets,
  };
});
