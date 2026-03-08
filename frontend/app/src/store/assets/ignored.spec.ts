import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';

describe('useIgnoredAssetsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('should add an ignored asset', () => {
    const store = useIgnoredAssetsStore();
    const { ignoredAssets } = storeToRefs(store);

    expect(get(ignoredAssets)).toEqual([]);

    store.addIgnoredAsset('ETH');
    expect(get(ignoredAssets)).toEqual(['ETH']);
  });

  it('should not add duplicate ignored asset', () => {
    const store = useIgnoredAssetsStore();
    const { ignoredAssets } = storeToRefs(store);

    store.addIgnoredAsset('ETH');
    store.addIgnoredAsset('ETH');
    expect(get(ignoredAssets)).toEqual(['ETH']);
  });

  it('should return correct result for isAssetIgnored', () => {
    const store = useIgnoredAssetsStore();

    store.addIgnoredAsset('ETH');

    expect(store.isAssetIgnored('ETH')).toBe(true);
    expect(store.isAssetIgnored('BCH')).toBe(false);
  });

  it('should return correct result for useIsAssetIgnored', () => {
    const store = useIgnoredAssetsStore();

    store.addIgnoredAsset('ETH');

    const ethIgnored = store.useIsAssetIgnored('ETH');
    const bchIgnored = store.useIsAssetIgnored('BCH');
    expect(get(ethIgnored)).toBe(true);
    expect(get(bchIgnored)).toBe(false);
  });
});
