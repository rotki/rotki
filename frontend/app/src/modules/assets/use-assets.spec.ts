import type { useAssetIconApi } from '@/modules/assets/api/use-asset-icon-api';
import type { AssetMergePayload, AssetUpdatePayload } from '@/modules/assets/types';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetsApi } from '@/modules/assets/api/use-assets-api';
import { useAssets } from '@/modules/assets/use-assets';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

const runTaskMock = vi.fn();

vi.mock('@/modules/assets/api/use-assets-api', () => ({
  useAssetsApi: vi.fn().mockReturnValue({
    checkForAssetUpdate: vi.fn().mockResolvedValue({ taskId: 1 }),
    performUpdate: vi.fn().mockResolvedValue({ taskId: 1 }),
    mergeAssets: vi.fn().mockResolvedValue(true),
    importCustom: vi.fn().mockResolvedValue({ taskId: 1 }),
    exportCustom: vi.fn().mockResolvedValue({ taskId: 1 }),
  }),
}));

vi.mock('@/modules/assets/api/use-asset-icon-api', () => ({
  useAssetIconApi: vi.fn().mockReturnValue({
    checkAsset: vi.fn().mockResolvedValue(404),
  } satisfies Partial<ReturnType<typeof useAssetIconApi>>),
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

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: vi.fn().mockReturnValue({
    notify: vi.fn(),
  }),
}));

vi.mock('@/modules/core/notifications/use-notifications-store/index', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({
    removeMatching: vi.fn(),
  }),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => {
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
    vi.clearAllMocks();
    store = useAssets();
    api = useAssetsApi();
  });

  describe('checkForUpdate', () => {
    it('should detect available update', async () => {
      const versions = {
        local: 14,
        remote: 16,
        newChanges: 2,
      };

      runTaskMock.mockResolvedValue({ success: true, result: versions });

      const result = await store.checkForUpdate();

      expect(api.checkForAssetUpdate).toHaveBeenCalledOnce();
      expect(useNotificationDispatcher().notify).not.toHaveBeenCalled();
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

      runTaskMock.mockResolvedValue({ success: true, result: versions });

      const result = await store.checkForUpdate();

      expect(api.checkForAssetUpdate).toHaveBeenCalledOnce();
      expect(useNotificationDispatcher().notify).not.toHaveBeenCalled();
      expect(result).toEqual({
        updateAvailable: false,
        versions,
      });
    });

    it('should handle error', async () => {
      runTaskMock.mockResolvedValue({ success: false, message: 'failed', cancelled: false, backendCancelled: false, skipped: false });

      const result = await store.checkForUpdate();

      expect(api.checkForAssetUpdate).toHaveBeenCalledOnce();
      expect(result).toEqual({
        updateAvailable: false,
      });

      expect(useNotificationDispatcher().notify).toHaveBeenCalled();
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
      runTaskMock.mockResolvedValue({ success: true, result: true });

      const result = await store.applyUpdates(payload);

      expect(api.performUpdate).toHaveBeenCalledOnce();
      expect(useNotificationDispatcher().notify).not.toHaveBeenCalled();
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

      runTaskMock.mockResolvedValue({ success: true, result: conflicts });

      const result = await store.applyUpdates(payload);

      expect(api.performUpdate).toHaveBeenCalledOnce();
      expect(useNotificationDispatcher().notify).not.toHaveBeenCalled();
      expect(result).toEqual({
        done: false,
        conflicts,
      });
    });

    it('should handle error', async () => {
      runTaskMock.mockResolvedValue({ success: false, message: 'failed', cancelled: false, backendCancelled: false, skipped: false });

      const result = await store.applyUpdates(payload);

      expect(api.performUpdate).toHaveBeenCalledOnce();
      expect(result).toEqual({
        done: false,
      });

      expect(useNotificationDispatcher().notify).toHaveBeenCalled();
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
      runTaskMock.mockResolvedValue({ success: true, result: true });

      const result = await store.importCustomAssets(file);

      expect(api.importCustom).toHaveBeenCalledWith(file);

      expect(result).toEqual({
        success: true,
      });
    });

    it('should handle failure', async () => {
      runTaskMock.mockResolvedValue({ success: false, message: 'failed', cancelled: false, backendCancelled: false, skipped: false });

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
      runTaskMock.mockResolvedValue({ success: true, result: { filePath: 'export.csv' } });

      const result = await store.exportCustomAssets();

      expect(api.exportCustom).toHaveBeenCalledWith(directory);

      expect(result).toEqual({
        directory,
        filePath: 'export.csv',
      });
    });

    it('should handle failure', async () => {
      vi.mocked(api.exportCustom).mockResolvedValue({ taskId: 1 });
      runTaskMock.mockResolvedValue({ success: false, message: 'failed', cancelled: false, backendCancelled: false, skipped: false });

      const result = await store.exportCustomAssets();

      expect(api.exportCustom).toHaveBeenCalledWith(directory);

      expect(result).toEqual({
        success: false,
        message: 'failed',
      });
    });
  });
});
