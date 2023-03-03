import { type NftResponse } from '@/types/nfts';

vi.mock('@/composables/api/assets/index', () => ({
  useAssetsApi: vi.fn().mockReturnValue({
    fetchNfts: vi.fn().mockResolvedValue(1)
  })
}));

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    awaitTask: vi.fn().mockResolvedValue({})
  })
}));

describe('store::assets/nft', () => {
  setActivePinia(createPinia());
  let store: ReturnType<typeof useNftsStore>;
  let api: ReturnType<typeof useAssetsApi>;

  beforeEach(() => {
    store = useNftsStore();
    api = useAssetsApi();
    vi.clearAllMocks();
  });

  describe('fetchNfts', () => {
    test('success', async () => {
      const nfts: NftResponse = {
        addresses: {
          '0x443E1f9b1c866E54e914822B7d3d7165EdB6e9Ea': []
        },
        entriesFound: 0,
        entriesLimit: 0
      };

      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: nfts,
        meta: { title: '' }
      });

      const result = await store.fetchNfts(true);

      expect(api.fetchNfts).toHaveBeenCalledWith(true);

      expect(result).toEqual({
        result: nfts,
        message: ''
      });
    });

    test('failed', async () => {
      vi.mocked(useTaskStore().awaitTask).mockRejectedValue(
        new Error('failed')
      );

      const result = await store.fetchNfts(true);

      expect(api.fetchNfts).toHaveBeenCalledWith(true);

      expect(result).toEqual({
        result: null,
        message: 'failed'
      });
    });
  });
});
