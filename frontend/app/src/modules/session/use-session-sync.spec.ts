import type { TaskResult } from '@/modules/core/tasks/use-task-handler';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SYNC_DOWNLOAD, SYNC_UPLOAD } from '@/modules/session/sync';
import { useSync } from '@/modules/session/use-session-sync';

const mockRunTask = vi.fn();
const mockIsTaskRunning = vi.fn((): boolean => false);
const mockNotifyError = vi.fn();
const mockNotifyInfo = vi.fn();
const mockForceSync = vi.fn();
const { mockCancelAllQueued, mockCancel } = vi.hoisted(() => ({ mockCancel: vi.fn(), mockCancelAllQueued: vi.fn() }));

vi.mock('@/modules/core/tasks/use-task-handler', () => ({
  isActionableFailure: vi.fn((outcome: TaskResult<unknown>): boolean =>
    !outcome.success && !('cancelled' in outcome && outcome.cancelled) && !('skipped' in outcome && outcome.skipped),
  ),
  useTaskHandler: vi.fn(() => ({
    runTask: mockRunTask,
  })),
}));

vi.mock('@/modules/core/tasks/use-task-store', () => ({
  useTaskStore: vi.fn(() => ({
    isTaskRunning: mockIsTaskRunning,
  })),
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
  api: {
    cancel: mockCancel,
    cancelAllQueued: mockCancelAllQueued,
  },
}));

describe('useSync', () => {
  let sync: ReturnType<typeof useSync>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockIsTaskRunning.mockReturnValue(false);
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
      mockIsTaskRunning.mockReturnValue(true);
      const logout = vi.fn(async (): Promise<void> => {});

      await sync.forceSync(logout);

      expect(mockRunTask).not.toHaveBeenCalled();
      expect(logout).not.toHaveBeenCalled();
    });

    it('should cancel in-flight requests before syncing', async () => {
      mockRunTask.mockResolvedValue({ result: false, success: true });
      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(mockCancelAllQueued).toHaveBeenCalledOnce();
      expect(mockCancel).toHaveBeenCalledOnce();
    });

    it('should close the confirmation dialog before an upload sync', async () => {
      set(sync.syncAction, SYNC_UPLOAD);
      set(sync.displaySyncConfirmation, true);
      mockRunTask.mockResolvedValue({ result: true, success: true });

      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(get(sync.displaySyncConfirmation)).toBe(false);
    });

    it('should notify and log out on a successful download sync', async () => {
      set(sync.syncAction, SYNC_DOWNLOAD);
      mockRunTask.mockResolvedValue({ result: true, success: true });
      const logout = vi.fn(async (): Promise<void> => {});

      await sync.forceSync(logout);

      expect(mockNotifyInfo).toHaveBeenCalledOnce();
      expect(logout).toHaveBeenCalledOnce();
    });

    it('should not log out on a successful upload sync', async () => {
      set(sync.syncAction, SYNC_UPLOAD);
      mockRunTask.mockResolvedValue({ result: true, success: true });
      const logout = vi.fn(async (): Promise<void> => {});

      await sync.forceSync(logout);

      expect(mockNotifyInfo).toHaveBeenCalledOnce();
      expect(logout).not.toHaveBeenCalled();
    });

    it('should notify a failure when the task succeeds but returns false', async () => {
      mockRunTask.mockResolvedValue({ message: 'nope', result: false, success: true });

      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(mockNotifyError).toHaveBeenCalledOnce();
      expect(mockNotifyInfo).not.toHaveBeenCalled();
    });

    it('should notify a failure on an actionable task failure', async () => {
      mockRunTask.mockResolvedValue({ cancelled: false, message: 'boom', skipped: false, success: false });

      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(mockNotifyError).toHaveBeenCalledOnce();
    });

    it('should stay silent on a cancelled task', async () => {
      mockRunTask.mockResolvedValue({ cancelled: true, message: 'cancelled', skipped: false, success: false });

      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(mockNotifyError).not.toHaveBeenCalled();
      expect(mockNotifyInfo).not.toHaveBeenCalled();
    });
  });
});
