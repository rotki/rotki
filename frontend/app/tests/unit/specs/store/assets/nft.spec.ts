import type { NftResponse } from '@/types/nfts';
import { useAssetsApi } from '@/composables/api/assets';
import { useNfts } from '@/composables/assets/nft';
import { useTaskStore } from '@/store/tasks';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/composables/api/assets/index', () => ({
  useAssetsApi: vi.fn().mockReturnValue({
    fetchNfts: vi.fn().mockResolvedValue(1),
  }),
}));

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    awaitTask: vi.fn().mockResolvedValue({}),
  }),
}));

describe('composables::nft', () => {
  setActivePinia(createPinia());
  let store: ReturnType<typeof useNfts>;
  let api: ReturnType<typeof useAssetsApi>;

  beforeEach(() => {
    store = useNfts();
    api = useAssetsApi();
    vi.clearAllMocks();
  });

  describe('fetchNfts', () => {
    it('success', async () => {
      const nfts: NftResponse = {
        addresses: {
          '0x443E1f9b1c866E54e914822B7d3d7165EdB6e9Ea': [],
        },
        entriesFound: 0,
        entriesLimit: 0,
      };

      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: nfts,
        meta: { title: '' },
      });

      const result = await store.fetchNfts(true);

      expect(api.fetchNfts).toHaveBeenCalledWith(true);

      expect(result).toEqual({
        result: nfts,
        message: '',
      });
    });

    it('failed', async () => {
      vi.mocked(useTaskStore().awaitTask).mockRejectedValue(new Error('failed'));

      const result = await store.fetchNfts(true);

      expect(api.fetchNfts).toHaveBeenCalledWith(true);

      expect(result).toEqual({
        result: null,
        message: 'failed',
      });
    });
  });
});
