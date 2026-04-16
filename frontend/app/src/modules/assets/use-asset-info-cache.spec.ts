import type { AssetMap } from '@/modules/assets/types';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetInfoApi } from '@/modules/assets/api/use-asset-info-api';

describe('modules/assets/use-asset-info-cache', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.resetModules();
    setActivePinia(createPinia());
    vi.mocked(useAssetInfoApi().assetMapping).mockReset();
  });

  async function getCache(): Promise<ReturnType<typeof import('./use-asset-info-cache').useAssetInfoCache>> {
    const { useAssetInfoCache } = await import('./use-asset-info-cache');
    return useAssetInfoCache();
  }

  it('should cache assets', async () => {
    const cache = await getCache();
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
    cache.resolve('KEY');
    cache.resolve('KEY');
    vi.advanceTimersByTime(2500);
    await flushPromises();
    expect(useAssetInfoApi().assetMapping).toHaveBeenCalledOnce();
    expect(cache.resolve('KEY')).toEqual(asset);
  });

  it('should not request failed assets twice unless they expire', async () => {
    const cache = await getCache();
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue({
      assetCollections: {},
      assets: {},
    });
    cache.resolve('KEY');
    cache.resolve('KEY');
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(useAssetInfoApi().assetMapping).toHaveBeenCalledOnce();
    expect(cache.resolve('KEY')).toBeNull();
    vi.advanceTimersByTime(1000 * 60 * 11);
    cache.resolve('KEY');
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(cache.resolve('KEY')).toBeNull();
    expect(useAssetInfoApi().assetMapping).toHaveBeenCalledTimes(2);
  });

  it('should only re-request asset if cache entry expires', async () => {
    const cache = await getCache();
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
    cache.resolve('KEY');
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(useAssetInfoApi().assetMapping).toHaveBeenCalledOnce();
    expect(cache.resolve('KEY')).toEqual(asset);
    vi.advanceTimersByTime(1000 * 60 * 11);
    cache.resolve('KEY');
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(useAssetInfoApi().assetMapping).toHaveBeenCalledTimes(2);
    expect(cache.resolve('KEY')).toEqual(asset);
  });

  it('should stop caching assets after cache limit is reached', async () => {
    const cache = await getCache();
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

    cache.resolve(`AST-0`);
    vi.advanceTimersByTime(3000);
    await flushPromises();

    for (let i = 1; i < 50; i++) cache.resolve(`AST-${i}`);

    vi.advanceTimersByTime(4000);
    await flushPromises();

    cache.resolve(`AST-0`);
    vi.advanceTimersByTime(4000);
    await flushPromises();

    for (let i = 51; i < 505; i++) cache.resolve(`AST-${i}`);

    vi.advanceTimersByTime(4000);
    await flushPromises();

    const entries = Object.entries(get(cache.cache));
    expect(entries).toHaveLength(500);
    expect(entries.map(([id]) => id)).toContain('AST-0');
  });

  it('should not delete cache if the request after expiry hits any error', async () => {
    const cache = await getCache();
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
      cache.resolve(`AST-${i}`);
    }

    vi.advanceTimersByTime(4000);
    await flushPromises();

    const entries = Object.entries(get(cache.cache));
    expect(entries).toHaveLength(50);

    vi.advanceTimersByTime(600_000);
    await flushPromises();

    vi.mocked(assetMapping).mockRejectedValue(new Error('Network error'));

    for (let i = 0; i < 50; i++) {
      cache.resolve(`AST-${i}`);
    }

    vi.advanceTimersByTime(4000);
    await flushPromises();

    const secondPart = Object.entries(get(cache.cache));
    expect(secondPart).toHaveLength(50);
  });
});
