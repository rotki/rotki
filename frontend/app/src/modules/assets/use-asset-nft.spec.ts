import type { NftResponse } from '@/modules/assets/nfts';
import { createCustomPinia } from '@test/utils/create-pinia';
import { runSpecWith } from '@test/utils/mocks/native-task';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetsApi } from '@/modules/assets/api/use-assets-api';
import { useNfts } from '@/modules/assets/use-asset-nft';
import { TaskFailed } from '@/modules/core/tasks/task-result';

const runTaskResult = vi.fn();

/** Runs the submitted spec inline so assertions see the real `run` body. */
const submitTask = vi.fn(runSpecWith(runTaskResult));

vi.mock('@/modules/assets/api/use-assets-api', () => ({
  useAssetsApi: vi.fn().mockReturnValue({
    fetchNfts: vi.fn().mockResolvedValue({ taskId: 1 }),
  }),
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn(() => ({
    cancelByType: vi.fn(() => vi.fn()),
    runTaskResult,
    statusOf: vi.fn(),
    submitTask,
  })),
}));

describe('useNftStore', () => {
  let store: ReturnType<typeof useNfts>;
  let api: ReturnType<typeof useAssetsApi>;

  beforeEach(() => {
    setActivePinia(createCustomPinia());
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

      runTaskResult.mockImplementation(async (task: () => Promise<unknown>) => {
        await task();
        return ok(nfts);
      });

      const result = await store.fetchNfts(true);

      expect(api.fetchNfts).toHaveBeenCalledWith(true);

      expect(result).toEqual({
        result: nfts,
        message: '',
      });
    });

    it('should handle failure', async () => {
      runTaskResult.mockResolvedValue(err(TaskFailed({ message: 'failed' })));

      const result = await store.fetchNfts(true);

      expect(result).toEqual({
        result: null,
        message: 'failed',
      });
    });
  });
});
