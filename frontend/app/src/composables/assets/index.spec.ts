import type { useAssetIconApi } from '@/composables/api/assets/icon';
import type { AssetMergePayload, AssetUpdatePayload } from '@/types/asset';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetsApi } from '@/composables/api/assets';
import { useAssets } from '@/composables/assets';
import { useInterop } from '@/composables/electron-interop';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';

vi.mock('@/composables/api/assets/index', () => ({
  useAssetsApi: vi.fn().mockReturnValue({
    checkForAssetUpdate: vi.fn().mockResolvedValue({ taskId: 1 }),
    performUpdate: vi.fn().mockResolvedValue({ taskId: 1 }),
    mergeAssets: vi.fn().mockResolvedValue(true),
    importCustom: vi.fn().mockResolvedValue({ taskId: 1 }),
    exportCustom: vi.fn().mockResolvedValue({ taskId: 1 }),
  }),
}));

vi.mock('@/composables/api/assets/icon', () => ({
  useAssetIconApi: vi.fn().mockReturnValue({
    checkAsset: vi.fn().mockResolvedValue(404),
  } satisfies Partial<ReturnType<typeof useAssetIconApi>>),
}));

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    awaitTask: vi.fn().mockResolvedValue({}),
  }),
}));

vi.mock('@/store/notifications/index', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({
    notify: vi.fn().mockReturnValue({}),
  }),
}));

vi.mock('@/composables/electron-interop', () => {
  const mockInterop = {
    appSession: vi.fn(),
    openDirectory: vi.fn(),
    getPath: vi.fn().mockReturnValue(undefined),
  };
  return {
    useInterop: vi.fn().mockReturnValue(mockInterop),
    interop: mockInterop,
  };
});

vi.mock('');

describe('useAssets', () => {
  setActivePinia(createPinia());
  let store: ReturnType<typeof useAssets>;
  let api: ReturnType<typeof useAssetsApi>;

  beforeEach(() => {
    store = useAssets();
    api = useAssetsApi();
    vi.clearAllMocks();
  });

  describe('checkForUpdate', () => {
    it('should detect available update', async () => {
      const versions = {
        local: 14,
        remote: 16,
        newChanges: 2,
      };

      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: versions,
        meta: { title: '' },
      });

      const result = await store.checkForUpdate();

      expect(api.checkForAssetUpdate).toHaveBeenCalledOnce();
      expect(useNotificationsStore().notify).not.toHaveBeenCalled();
      expect(result).toEqual({
        updateAvailable: true,
        versions,
      });
    });

    it('should detect no available update', async () => {
      const versions = {
        local: 14,
        remote: 14,
        newChanges: 2,
      };

      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: versions,
        meta: { title: '' },
      });

      const result = await store.checkForUpdate();

      expect(api.checkForAssetUpdate).toHaveBeenCalledOnce();
      expect(useNotificationsStore().notify).not.toHaveBeenCalled();
      expect(result).toEqual({
        updateAvailable: false,
        versions,
      });
    });

    it('should handle error', async () => {
      vi.mocked(useTaskStore().awaitTask).mockRejectedValue(new Error('failed'));

      const result = await store.checkForUpdate();

      expect(api.checkForAssetUpdate).toHaveBeenCalledOnce();
      expect(result).toEqual({
        updateAvailable: false,
      });

      expect(useNotificationsStore().notify).toHaveBeenCalled();
    });
  });

  describe('applyUpdates', () => {
    const payload: AssetUpdatePayload = {
      version: 16,
      resolution: {
        ETH: 'local',
      },
    };

    it('should complete successfully', async () => {
      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: true,
        meta: { title: '' },
      });

      const result = await store.applyUpdates(payload);

      expect(api.performUpdate).toHaveBeenCalledOnce();
      expect(useNotificationsStore().notify).not.toHaveBeenCalled();
      expect(result).toEqual({
        done: true,
      });
    });

    it('should complete with chain identifier', async () => {
      const conflicts = [
        {
          identifier: 'ETH',
          local: {},
          remote: {},
        },
      ];

      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: conflicts,
        meta: { title: '' },
      });

      const result = await store.applyUpdates(payload);

      expect(api.performUpdate).toHaveBeenCalledOnce();
      expect(useNotificationsStore().notify).not.toHaveBeenCalled();
      expect(result).toEqual({
        done: false,
        conflicts,
      });
    });

    it('should handle error', async () => {
      vi.mocked(useTaskStore().awaitTask).mockRejectedValue(new Error('failed'));

      const result = await store.applyUpdates(payload);

      expect(api.performUpdate).toHaveBeenCalledOnce();
      expect(result).toEqual({
        done: false,
      });

      expect(useNotificationsStore().notify).toHaveBeenCalled();
    });
  });

  describe('mergeAssets', () => {
    const payload: AssetMergePayload = {
      sourceIdentifier: 'ETH2',
      targetIdentifier: 'ETH',
    };

    it('should succeed', async () => {
      vi.mocked(api.mergeAssets).mockResolvedValue(true);

      const result = await store.mergeAssets(payload);

      expect(api.mergeAssets).toHaveBeenCalledWith(payload.sourceIdentifier, payload.targetIdentifier);

      expect(result).toEqual({
        success: true,
      });
    });

    it('should handle failure', async () => {
      vi.mocked(api.mergeAssets).mockRejectedValue(new Error('failed'));

      const result = await store.mergeAssets(payload);

      expect(api.mergeAssets).toHaveBeenCalledWith(payload.sourceIdentifier, payload.targetIdentifier);

      expect(result).toEqual({
        success: false,
        message: 'failed',
      });
    });
  });

  describe('importCustomAssets', () => {
    const file = new File(['0'], 'test.csv');

    it('should succeed', async () => {
      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: true,
        meta: { title: '' },
      });

      const result = await store.importCustomAssets(file);

      expect(api.importCustom).toHaveBeenCalledWith(file);

      expect(result).toEqual({
        success: true,
      });
    });

    it('should handle failure', async () => {
      vi.mocked(useTaskStore().awaitTask).mockRejectedValue(new Error('failed'));

      const result = await store.importCustomAssets(file);

      expect(api.importCustom).toHaveBeenCalledWith(file);

      expect(result).toEqual({
        success: false,
        message: 'failed',
      });
    });
  });

  describe('exportCustomAsset', () => {
    const directory = 'filepath.csv';
    beforeEach(() => {
      vi.mocked(useInterop().openDirectory).mockResolvedValue(directory);
    });

    it('should succeed', async () => {
      vi.mocked(api.exportCustom).mockResolvedValue({ taskId: 1 });
      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: true,
        meta: { title: '' },
      });

      const result = await store.exportCustomAssets();

      expect(api.exportCustom).toHaveBeenCalledWith(directory);

      expect(result).toEqual({
        directory,
      });
    });

    it('should handle failure', async () => {
      vi.mocked(api.exportCustom).mockResolvedValue({ taskId: 1 });
      vi.mocked(useTaskStore().awaitTask).mockRejectedValue(new Error('failed'));

      const result = await store.exportCustomAssets();

      expect(api.exportCustom).toHaveBeenCalledWith(directory);

      expect(result).toEqual({
        success: false,
        message: 'failed',
      });
    });
  });
});
