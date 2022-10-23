import { AssetInfo } from '@rotki/common/lib/data';
import flushPromises from 'flush-promises';
import { ComputedRef } from 'vue';
import { useAssetInfoApi } from '@/services/assets/info';
import { useAssetCacheStore } from '@/store/assets/asset-cache';
import { AssetMap } from '@/types/assets';

vi.mock('@/services/assets/info', () => ({
  useAssetInfoApi: vi.fn().mockReturnValue({
    assetMapping: vi.fn().mockResolvedValue({})
  })
}));

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
      name: 'KEY Asset',
      symbol: 'KEY'
    };
    const mapping: AssetMap = { [key]: asset };
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue(mapping);
    const firstRetrieval: ComputedRef<AssetInfo | null> = store.retrieve('KEY');
    const secondRetrieval: ComputedRef<AssetInfo | null> =
      store.retrieve('KEY');
    vi.advanceTimersByTime(2500);
    await flushPromises();
    expect(useAssetInfoApi().assetMapping).toHaveBeenCalledOnce();
    expect(get(firstRetrieval)).toEqual(asset);
    expect(get(secondRetrieval)).toEqual(asset);
  });

  it('should not request failed assets twice unless they expire', async () => {
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue({});
    const firstRetrieval: ComputedRef<AssetInfo | null> = store.retrieve('KEY');
    const secondRetrieval: ComputedRef<AssetInfo | null> =
      store.retrieve('KEY');
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
      name: 'KEY Asset',
      symbol: 'KEY'
    };
    const mapping: AssetMap = { [key]: asset };
    vi.mocked(useAssetInfoApi().assetMapping).mockResolvedValue(mapping);
    const firstRetrieval: ComputedRef<AssetInfo | null> = store.retrieve('KEY');
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(useAssetInfoApi().assetMapping).toHaveBeenCalledOnce();
    expect(get(firstRetrieval)).toEqual(asset);
    vi.advanceTimersByTime(1000 * 60 * 11);
    const secondRetrieval: ComputedRef<AssetInfo | null> =
      store.retrieve('KEY');
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(useAssetInfoApi().assetMapping).toHaveBeenCalledTimes(2);
    expect(get(secondRetrieval)).toEqual(asset);
  });

  it('should stop caching assets after cache limit is reached', async () => {
    vi.mocked(useAssetInfoApi().assetMapping).mockImplementation(
      async identifier => {
        const mapping: AssetMap = {};
        for (const id of identifier) {
          mapping[id] = {
            symbol: id,
            name: `name ${id}`
          };
        }
        return mapping;
      }
    );

    store.retrieve(`AST-0`);
    vi.advanceTimersByTime(3000);
    await flushPromises();

    for (let i = 1; i < 50; i++) {
      store.retrieve(`AST-${i}`);
    }

    vi.advanceTimersByTime(4000);
    await flushPromises();

    store.retrieve(`AST-0`);
    vi.advanceTimersByTime(4000);
    await flushPromises();

    for (let i = 51; i < 505; i++) {
      store.retrieve(`AST-${i}`);
    }
    vi.advanceTimersByTime(4000);
    await flushPromises();

    const entries = Object.entries(get(store.cache));
    expect(entries).toHaveLength(500);
    expect(entries.map(([id]) => id)).toContain('AST-0');
  });
});
