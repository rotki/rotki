import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetIgnoreApi } from '@/composables/api/assets/ignore';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';

vi.mock('@/composables/api/assets/ignore', () => ({
  useAssetIgnoreApi: vi.fn().mockReturnValue({
    getIgnoredAssets: vi.fn().mockResolvedValue([]),
    addIgnoredAssets: vi.fn().mockResolvedValue([]),
    removeIgnoredAssets: vi.fn().mockResolvedValue({ successful: [], noAction: [] }),
  }),
}));

describe('useIgnoredAssetsStore', () => {
  setActivePinia(createPinia());
  const store: ReturnType<typeof useIgnoredAssetsStore> = useIgnoredAssetsStore();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch the ignored assets', async () => {
    const mockIgnoredAssets = ['ETH'];
    const { ignoredAssets } = storeToRefs(store);

    expect(get(ignoredAssets)).toEqual([]);
    vi.mocked(useAssetIgnoreApi().getIgnoredAssets).mockResolvedValue(mockIgnoredAssets);
    await store.fetchIgnoredAssets();
    expect(useAssetIgnoreApi().getIgnoredAssets).toHaveBeenCalledOnce();
    expect(get(ignoredAssets)).toEqual(mockIgnoredAssets);
  });

  it('should add ignored asset', async () => {
    vi.mocked(useAssetIgnoreApi().addIgnoredAssets).mockResolvedValue({ successful: ['ETH', 'DAI'], noAction: [] });
    await store.ignoreAsset('DAI');
    expect(useAssetIgnoreApi().addIgnoredAssets).toHaveBeenCalledWith(['DAI']);
  });

  it('should remove ignored asset', async () => {
    vi.mocked(useAssetIgnoreApi().addIgnoredAssets).mockResolvedValue({ successful: ['ETH'], noAction: [] });
    await store.ignoreAsset('DAI');
    expect(useAssetIgnoreApi().addIgnoredAssets).toHaveBeenCalledWith(['DAI']);
  });

  it('should not ignored asset if already ignored', async () => {
    vi.mocked(useAssetIgnoreApi().addIgnoredAssets).mockResolvedValue({
      successful: ['ETH', 'DAI'],
      noAction: ['DAI'],
    });
    await store.ignoreAsset('DAI');
    expect(useAssetIgnoreApi().addIgnoredAssets).toHaveBeenCalledWith(['DAI']);
  });

  it('should return correct result for isAssetIgnored', () => {
    const { useIsAssetIgnored } = store;

    const ethIgnored = useIsAssetIgnored('ETH');
    const bchIgnored = useIsAssetIgnored('BCH');
    expect(get(ethIgnored)).toBe(true);
    expect(get(bchIgnored)).toBe(false);
  });
});
