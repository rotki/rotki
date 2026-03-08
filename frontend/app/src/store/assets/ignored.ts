import type { MaybeRefOrGetter } from 'vue';

export const useIgnoredAssetsStore = defineStore('assets/ignored', () => {
  const ignoredAssets = shallowRef<string[]>([]);

  const isAssetIgnored = (asset: string): boolean => get(ignoredAssets).includes(asset);

  function useIsAssetIgnored(asset: MaybeRefOrGetter<string>): ComputedRef<boolean> {
    return computed<boolean>(() => isAssetIgnored(toValue(asset)));
  }

  const addIgnoredAsset = (asset: string): void => {
    const ignored = get(ignoredAssets);
    if (!ignored.includes(asset))
      set(ignoredAssets, [...ignored, asset]);
  };

  return {
    addIgnoredAsset,
    ignoredAssets,
    isAssetIgnored,
    useIsAssetIgnored,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useIgnoredAssetsStore, import.meta.hot));
