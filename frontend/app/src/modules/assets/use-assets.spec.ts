import type { useAssetIconApi } from '@/modules/assets/api/use-asset-icon-api';
import type { AssetMergePayload, AssetUpdatePayload } from '@/modules/assets/types';
import { createMock } from '@test/utils/create-mock';
import { createCustomPinia } from '@test/utils/create-pinia';
import { runSpecWith } from '@test/utils/mocks/native-task';
import { err, ok, type Result } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetsApi } from '@/modules/assets/api/use-assets-api';
import { useAssets } from '@/modules/assets/use-assets';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

const runTaskResult = vi.fn();

/** Runs the submitted spec inline so assertions see the real `run` body. */
const submitTask = vi.fn(runSpecWith(runTaskResult));

/** Drives the native `run`: invoke the api call, then yield the given plainfp outcome. */
function whenTask<R>(outcome: Result<R, TaskError>): void {
  runTaskResult.mockImplementation(async (task: () => Promise<unknown>): Promise<Result<R, TaskError>> => {
    await task();
    return outcome;
  });
}

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

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn(() => ({
    cancelByType: vi.fn(() => vi.fn()),
    runTaskResult,
    statusOf: vi.fn(),
    submitTask,
  })),
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

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: vi.fn().mockReturnValue(createMock<ReturnType<typeof useInterop>>({
    // A boolean, not a function: the export path branches on it directly.
    appSession: true,
    getPath: vi.fn().mockReturnValue(undefined),
    openDirectory: vi.fn(),
  })),
}));

describe('useAssets', () => {
  let store: ReturnType<typeof useAssets>;
  let api: ReturnType<typeof useAssetsApi>;

  beforeEach(() => {
    setActivePinia(createCustomPinia());
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

      whenTask(ok(versions));

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

      whenTask(ok(versions));

      const result = await store.checkForUpdate();

      expect(api.checkForAssetUpdate).toHaveBeenCalledOnce();
      expect(useNotificationDispatcher().notify).not.toHaveBeenCalled();
      expect(result).toEqual({
        updateAvailable: false,
        versions,
      });
    });

    it('should handle error', async () => {
      whenTask(err(TaskFailed({ message: 'failed' })));

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
      whenTask(ok(true));

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

      whenTask(ok(conflicts));

      const result = await store.applyUpdates(payload);

      expect(api.performUpdate).toHaveBeenCalledOnce();
      expect(useNotificationDispatcher().notify).not.toHaveBeenCalled();
      expect(result).toEqual({
        done: false,
        conflicts,
      });
    });

    it('should handle error', async () => {
      whenTask(err(TaskFailed({ message: 'failed' })));

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
      whenTask(ok(true));

      const result = await store.importCustomAssets(file);

      expect(api.importCustom).toHaveBeenCalledWith(file);

      expect(result).toEqual({
        success: true,
      });
    });

    it('should handle failure', async () => {
      whenTask(err(TaskFailed({ message: 'failed' })));

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
      whenTask(ok({ filePath: 'export.csv' }));

      const result = await store.exportCustomAssets();

      expect(api.exportCustom).toHaveBeenCalledWith(directory);

      expect(result).toEqual({
        directory,
        filePath: 'export.csv',
      });
    });

    it('should handle failure', async () => {
      vi.mocked(api.exportCustom).mockResolvedValue({ taskId: 1 });
      whenTask(err(TaskFailed({ message: 'failed' })));

      const result = await store.exportCustomAssets();

      expect(api.exportCustom).toHaveBeenCalledWith(directory);

      expect(result).toEqual({
        success: false,
        message: 'failed',
      });
    });
  });
});
