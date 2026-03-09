import type { AssetMap } from '@/types/asset';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useAssetCacheStore } from '@/store/assets/asset-cache';

describe('store::assets/cache', () => {
  let store: ReturnType<typeof useAssetCacheStore>;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.resetModules();
    setActivePinia(createPinia());
    store = useAssetCacheStore();
    vi.mocked(useAssetInfoApi().assetMapping).mockReset();
  });

  it('should delegate to useAssetInfoCache', async () => {
    const key = 'KEY';
    const asset = {
      isCustomAsset: false,
      name: 'KEY Asset',
      symbol: 'KEY',
    };
    const mapping: AssetMap = {
      assetCollections: {},
      assets: { [key]: asset },
    };
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue(mapping);
    store.resolve('KEY');
    vi.advanceTimersByTime(2500);
    await flushPromises();
    expect(useAssetInfoApi().assetMapping).toHaveBeenCalledOnce();
    expect(store.resolve('KEY')).toEqual(asset);
  });
});
