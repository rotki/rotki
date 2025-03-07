import { useAssetIgnoreApi } from '@/composables/api/assets/ignore';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/composables/api/assets/ignore', () => ({
  useAssetIgnoreApi: vi.fn().mockReturnValue({
    getIgnoredAssets: vi.fn().mockResolvedValue([]),
    addIgnoredAssets: vi.fn().mockResolvedValue([]),
    removeIgnoredAssets: vi.fn().mockResolvedValue({ successful: [], noAction: [] }),
  }),
}));

describe('store::assets/ignored', () => {
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

  it('isAssetIgnored return correct result', () => {
    const { isAssetIgnored } = store;

    expect(get(isAssetIgnored('ETH'))).toEqual(true);
    expect(get(isAssetIgnored('BCH'))).toEqual(false);
  });
});
