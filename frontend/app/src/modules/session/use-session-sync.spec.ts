import type { RotkiApi } from '@/modules/core/api/rotki-api';
import type { WorkStatus } from '@/modules/task-center/core/types';
import { createMock } from '@test/utils/create-mock';
import { runSpecWith } from '@test/utils/mocks/native-task';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { SYNC_DOWNLOAD, SYNC_UPLOAD } from '@/modules/session/sync';
import { useSync } from '@/modules/session/use-session-sync';

const mockNotifyError = vi.fn();
const mockNotifyInfo = vi.fn();
const mockForceSync = vi.fn();
const { mockCancelAllQueued, mockCancel } = vi.hoisted(() => ({ mockCancel: vi.fn(), mockCancelAllQueued: vi.fn() }));

const IDLE: WorkStatus = { active: false, everCompleted: false, pending: false, running: false };
let workStatus: WorkStatus = { ...IDLE };
const statusOf = vi.fn((): WorkStatus => workStatus);
const runTaskResult = vi.fn();

const submitTask = vi.fn(runSpecWith(runTaskResult));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn(() => ({ cancelByType: vi.fn(() => vi.fn()), runTaskResult, statusOf, submitTask })),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({
    notifyError: mockNotifyError,
    notifyInfo: mockNotifyInfo,
  })),
}));

vi.mock('@/modules/session/api/use-sync-api', () => ({
  useSyncApi: vi.fn(() => ({
    forceSync: mockForceSync,
  })),
}));

vi.mock('@/modules/core/api/rotki-api', () => ({
  api: createMock<RotkiApi>({
    cancel: mockCancel,
    cancelAllQueued: mockCancelAllQueued,
  }),
}));

describe('useSync', () => {
  let sync: ReturnType<typeof useSync>;

  beforeEach(() => {
    vi.clearAllMocks();
    workStatus = { ...IDLE };
    sync = useSync();
    set(sync.syncAction, SYNC_DOWNLOAD);
    set(sync.displaySyncConfirmation, false);
    set(sync.confirmChecked, false);
    set(sync.uploadStatus, null);
    set(sync.uploadProgress, undefined);
  });

  describe('confirmation dialog', () => {
    it('should show the confirmation dialog for the given action', () => {
      sync.showSyncConfirmation(SYNC_UPLOAD);

      expect(get(sync.syncAction)).toBe(SYNC_UPLOAD);
      expect(get(sync.displaySyncConfirmation)).toBe(true);
    });

    it('should reset the dialog state on cancel', () => {
      set(sync.displaySyncConfirmation, true);
      set(sync.confirmChecked, true);

      sync.cancelSync();

      expect(get(sync.displaySyncConfirmation)).toBe(false);
      expect(get(sync.confirmChecked)).toBe(false);
    });
  });

  describe('clearUploadStatus', () => {
    it('should clear the stored upload status and progress', () => {
      set(sync.uploadStatus, { actionable: false, message: null, uploaded: true });
      set(sync.uploadProgress, { currentChunk: 1, totalChunks: 2, type: 'uploading' });

      sync.clearUploadStatus();

      expect(get(sync.uploadStatus)).toBeNull();
      expect(get(sync.uploadProgress)).toBeUndefined();
    });
  });

  describe('forceSync', () => {
    it('should do nothing when a force sync task is already running', async () => {
      workStatus = { ...IDLE, active: true, running: true };
      const logout = vi.fn(async (): Promise<void> => {});

      await sync.forceSync(logout);

      expect(submitTask).not.toHaveBeenCalled();
      expect(logout).not.toHaveBeenCalled();
    });

    it('should cancel in-flight requests before syncing', async () => {
      runTaskResult.mockResolvedValue(ok(false));
      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(mockCancelAllQueued).toHaveBeenCalledOnce();
      expect(mockCancel).toHaveBeenCalledOnce();
    });

    it('should close the confirmation dialog before an upload sync', async () => {
      set(sync.syncAction, SYNC_UPLOAD);
      set(sync.displaySyncConfirmation, true);
      runTaskResult.mockResolvedValue(ok(true));

      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(get(sync.displaySyncConfirmation)).toBe(false);
    });

    it('should notify and log out on a successful download sync', async () => {
      set(sync.syncAction, SYNC_DOWNLOAD);
      runTaskResult.mockResolvedValue(ok(true));
      const logout = vi.fn(async (): Promise<void> => {});

      await sync.forceSync(logout);

      expect(mockNotifyInfo).toHaveBeenCalledOnce();
      expect(logout).toHaveBeenCalledOnce();
    });

    it('should not log out on a successful upload sync', async () => {
      set(sync.syncAction, SYNC_UPLOAD);
      runTaskResult.mockResolvedValue(ok(true));
      const logout = vi.fn(async (): Promise<void> => {});

      await sync.forceSync(logout);

      expect(mockNotifyInfo).toHaveBeenCalledOnce();
      expect(logout).not.toHaveBeenCalled();
    });

    it('should notify a failure when the task succeeds but returns false', async () => {
      runTaskResult.mockResolvedValue(ok(false));

      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(mockNotifyError).toHaveBeenCalledOnce();
      expect(mockNotifyInfo).not.toHaveBeenCalled();
    });

    it('should notify a failure on an actionable task failure', async () => {
      runTaskResult.mockResolvedValue(err(TaskFailed({ message: 'boom' })));

      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(mockNotifyError).toHaveBeenCalledOnce();
    });

    it('should stay silent on a cancelled task', async () => {
      runTaskResult.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(mockNotifyError).not.toHaveBeenCalled();
      expect(mockNotifyInfo).not.toHaveBeenCalled();
    });
  });
});
