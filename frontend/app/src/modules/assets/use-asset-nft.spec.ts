import type { NftResponse } from '@/modules/assets/nfts';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetsApi } from '@/modules/assets/api/use-assets-api';
import { useNfts } from '@/modules/assets/use-asset-nft';

const runTaskMock = vi.fn();

vi.mock('@/modules/assets/api/use-assets-api', () => ({
  useAssetsApi: vi.fn().mockReturnValue({
    fetchNfts: vi.fn().mockResolvedValue(1),
  }),
}));

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskHandler: vi.fn().mockReturnValue({
    runTask: async (taskFn: () => Promise<unknown>, ...rest: unknown[]): Promise<unknown> => {
      await taskFn();
      return runTaskMock(taskFn, ...rest);
    },
    cancelTask: vi.fn(),
    cancelTaskByTaskType: vi.fn(),
  }),
}));

describe('useNftStore', () => {
  setActivePinia(createPinia());
  let store: ReturnType<typeof useNfts>;
  let api: ReturnType<typeof useAssetsApi>;

  beforeEach(() => {
    vi.clearAllMocks();
    store = useNfts();
    api = useAssetsApi();
  });

  describe('fetchNfts', () => {
    it('should succeed', async () => {
      const nfts: NftResponse = {
        addresses: {
          '0x443E1f9b1c866E54e914822B7d3d7165EdB6e9Ea': [],
        },
        entriesFound: 0,
        entriesLimit: 0,
      };

      runTaskMock.mockResolvedValue({ success: true, result: nfts });

      const result = await store.fetchNfts(true);

      expect(api.fetchNfts).toHaveBeenCalledWith(true);

      expect(result).toEqual({
        result: nfts,
        message: '',
      });
    });

    it('should handle failure', async () => {
      runTaskMock.mockResolvedValue({ success: false, message: 'failed', cancelled: false, backendCancelled: false, skipped: false });

      const result = await store.fetchNfts(true);

      expect(api.fetchNfts).toHaveBeenCalledWith(true);

      expect(result).toEqual({
        result: null,
        message: 'failed',
      });
    });
  });
});
