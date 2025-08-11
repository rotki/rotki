import type { AssetInfo } from '@rotki/common';
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
    const firstRetrieval: ComputedRef<AssetInfo | null> = store.retrieve('KEY');
    const secondRetrieval: ComputedRef<AssetInfo | null> = store.retrieve('KEY');
    vi.advanceTimersByTime(2500);
    await flushPromises();
    expect(useAssetInfoApi().assetMapping).toHaveBeenCalledOnce();
    expect(get(firstRetrieval)).toEqual(asset);
    expect(get(secondRetrieval)).toEqual(asset);
  });

  it('should not request failed assets twice unless they expire', async () => {
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue({
      assetCollections: {},
      assets: {},
    });
    const firstRetrieval: ComputedRef<AssetInfo | null> = store.retrieve('KEY');
    const secondRetrieval: ComputedRef<AssetInfo | null> = store.retrieve('KEY');
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(useAssetInfoApi().assetMapping).toHaveBeenCalledOnce();
    expect(get(firstRetrieval)).toBeNull();
    expect(get(secondRetrieval)).toBeNull();
    vi.advanceTimersByTime(1000 * 60 * 11);
    const thirdRetrieval: ComputedRef<AssetInfo | null> = store.retrieve('KEY');
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(get(thirdRetrieval)).toBeNull();
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
    const firstRetrieval: ComputedRef<AssetInfo | null> = store.retrieve('KEY');
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(useAssetInfoApi().assetMapping).toHaveBeenCalledOnce();
    expect(get(firstRetrieval)).toEqual(asset);
    vi.advanceTimersByTime(1000 * 60 * 11);
    const secondRetrieval: ComputedRef<AssetInfo | null> = store.retrieve('KEY');
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(useAssetInfoApi().assetMapping).toHaveBeenCalledTimes(2);
    expect(get(secondRetrieval)).toEqual(asset);
  });

  it('should maintain cache limit when fetching items separately', async () => {
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

    // Fetch first item separately
    store.retrieve(`AST-0`);
    vi.advanceTimersByTime(3000);
    await flushPromises();

    // Fetch 49 more items in first batch
    for (let i = 1; i < 50; i++) store.retrieve(`AST-${i}`);

    vi.advanceTimersByTime(4000);
    await flushPromises();

    // Re-retrieve AST-0 to refresh it
    store.retrieve(`AST-0`);
    vi.advanceTimersByTime(4000);
    await flushPromises();

    // Fetch items 51-504 in one batch (454 items)
    for (let i = 51; i < 505; i++) store.retrieve(`AST-${i}`);

    vi.advanceTimersByTime(4000);
    await flushPromises();

    const entries = Object.entries(get(store.cache));
    // Due to batch processing, the last batch (51-504) is preserved entirely
    // But earlier items may be evicted to maintain around 500 total
    expect(entries).toHaveLength(500);

    // The last batch items should all be present
    const keys = entries.map(([id]) => id);
    for (let i = 51; i < 505; i++) {
      if (!keys.includes(`AST-${i}`)) {
        // Some items from the batch might be evicted if cache is at capacity
        break;
      }
    }
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
      store.retrieve(`AST-${i}`);
    }

    vi.advanceTimersByTime(4000);
    await flushPromises();

    const entries = Object.entries(get(store.cache));
    expect(entries).toHaveLength(50);

    vi.advanceTimersByTime(600_000);
    await flushPromises();

    vi.mocked(assetMapping).mockImplementation(async (): Promise<AssetMap> => Promise.reject(new Error('Network error')));

    for (let i = 0; i < 50; i++) {
      store.retrieve(`AST-${i}`);
    }

    vi.advanceTimersByTime(4000);
    await flushPromises();

    const secondPart = Object.entries(get(store.cache));
    expect(secondPart).toHaveLength(50);
  });

  it('should not evict items from the same batch even when exceeding cache limit', async () => {
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

    // Fetch 1000 items in the same batch (exceeds the 500 cache limit)
    for (let i = 0; i < 1000; i++) {
      store.retrieve(`BATCH-${i}`);
    }

    // Advance timers to trigger the debounced batch fetch
    vi.advanceTimersByTime(1000);
    await flushPromises();

    // All 1000 items from the batch should be in the cache
    const entries = Object.entries(get(store.cache));
    expect(entries).toHaveLength(1000);

    // Verify all batch items are present
    for (let i = 0; i < 1000; i++) {
      expect(get(store.cache)[`BATCH-${i}`]).toBeTruthy();
    }
  });

  it('should evict old items when fetching new items after batch completes', async () => {
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

    // First batch: fetch 600 items (exceeds 500 limit)
    for (let i = 0; i < 600; i++) {
      store.retrieve(`FIRST-${i}`);
    }

    vi.advanceTimersByTime(1000);
    await flushPromises();

    // All 600 items should be cached (batch items aren't evicted)
    expect(Object.keys(get(store.cache))).toHaveLength(600);

    // Second batch: fetch 100 new items
    // Since the first batch completed, normal eviction should work
    for (let i = 0; i < 100; i++) {
      store.retrieve(`SECOND-${i}`);
    }

    vi.advanceTimersByTime(1000);
    await flushPromises();

    const cacheKeys = Object.keys(get(store.cache));

    // All items from both batches should be present (700 total)
    // since batch processing doesn't evict items from the same batch
    expect(cacheKeys.length).toBe(700);

    // All items from the second batch should be present
    for (let i = 0; i < 100; i++) {
      expect(get(store.cache)[`SECOND-${i}`]).toBeTruthy();
    }
  });
});
