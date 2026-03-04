import type { AssetMap } from '@/types/asset';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useAssetCacheStore } from '@/store/assets/asset-cache';

describe('store::assets/cache', () => {
  let store: ReturnType<typeof useAssetCacheStore>;

  beforeEach(() => {
    vi.useFakeTimers();
    setActivePinia(createPinia());
    store = useAssetCacheStore();
    vi.mocked(useAssetInfoApi().assetMapping).mockReset();
  });

  it('should cache assets', async () => {
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
    store.resolve('KEY');
    vi.advanceTimersByTime(2500);
    await flushPromises();
    expect(useAssetInfoApi().assetMapping).toHaveBeenCalledOnce();
    expect(store.resolve('KEY')).toEqual(asset);
  });

  it('should not request failed assets twice unless they expire', async () => {
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue({
      assetCollections: {},
      assets: {},
    });
    store.resolve('KEY');
    store.resolve('KEY');
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(useAssetInfoApi().assetMapping).toHaveBeenCalledOnce();
    expect(store.resolve('KEY')).toBeNull();
    vi.advanceTimersByTime(1000 * 60 * 11);
    store.resolve('KEY');
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(store.resolve('KEY')).toBeNull();
    expect(useAssetInfoApi().assetMapping).toHaveBeenCalledTimes(2);
  });

  it('should only re-request asset if cache entry expires', async () => {
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
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(useAssetInfoApi().assetMapping).toHaveBeenCalledOnce();
    expect(store.resolve('KEY')).toEqual(asset);
    vi.advanceTimersByTime(1000 * 60 * 11);
    store.resolve('KEY');
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(useAssetInfoApi().assetMapping).toHaveBeenCalledTimes(2);
    expect(store.resolve('KEY')).toEqual(asset);
  });

  it('should stop caching assets after cache limit is reached', async () => {
    vi.mocked(useAssetInfoApi().assetMapping).mockImplementation(async (identifier): Promise<AssetMap> => {
      const mapping: AssetMap = { assetCollections: {}, assets: {} };
      for (const id of identifier) {
        mapping.assets[id] = {
          isCustomAsset: false,
          name: `name ${id}`,
          symbol: id,
        };
      }
      return Promise.resolve(mapping);
    });

    store.resolve(`AST-0`);
    vi.advanceTimersByTime(3000);
    await flushPromises();

    for (let i = 1; i < 50; i++) store.resolve(`AST-${i}`);

    vi.advanceTimersByTime(4000);
    await flushPromises();

    store.resolve(`AST-0`);
    vi.advanceTimersByTime(4000);
    await flushPromises();

    for (let i = 51; i < 505; i++) store.resolve(`AST-${i}`);

    vi.advanceTimersByTime(4000);
    await flushPromises();

    const entries = Object.entries(get(store.cache));
    expect(entries).toHaveLength(500);
    expect(entries.map(([id]) => id)).toContain('AST-0');
  });

  it('should not delete cache if the request after expiry hits any error', async () => {
    const assetMapping = useAssetInfoApi().assetMapping;
    vi.mocked(assetMapping).mockImplementation(async (identifier): Promise<AssetMap> => {
      const mapping: AssetMap = { assetCollections: {}, assets: {} };
      for (const id of identifier) {
        mapping.assets[id] = {
          isCustomAsset: false,
          name: `name ${id}`,
          symbol: id,
        };
      }
      return Promise.resolve(mapping);
    });

    for (let i = 0; i < 50; i++) {
      store.resolve(`AST-${i}`);
    }

    vi.advanceTimersByTime(4000);
    await flushPromises();

    const entries = Object.entries(get(store.cache));
    expect(entries).toHaveLength(50);

    vi.advanceTimersByTime(600_000);
    await flushPromises();

    vi.mocked(assetMapping).mockRejectedValue(new Error('Network error'));

    for (let i = 0; i < 50; i++) {
      store.resolve(`AST-${i}`);
    }

    vi.advanceTimersByTime(4000);
    await flushPromises();

    const secondPart = Object.entries(get(store.cache));
    expect(secondPart).toHaveLength(50);
  });
});
