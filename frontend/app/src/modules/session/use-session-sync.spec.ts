import type { RotkiApi } from '@/modules/core/api/rotki-api';
import type { WorkStatus } from '@/modules/task-center/core/types';
import { createMock } from '@test/utils/create-mock';
import { runSpecWith } from '@test/utils/mocks/native-task';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BackendCancelled, Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { SYNC_DOWNLOAD, SYNC_UPLOAD } from '@/modules/session/sync';
import { useSync } from '@/modules/session/use-session-sync';

const mockNotifyError = vi.fn();
const mockNotifyInfo = vi.fn();
const mockShowSuccessMessage = vi.fn();
const mockShowErrorMessage = vi.fn();
const mockColibriLogout = vi.fn<() => Promise<boolean>>();
const mockForceSync = vi.fn();
const { mockCancelAllQueued, mockCancel } = vi.hoisted(() => ({ mockCancel: vi.fn(), mockCancelAllQueued: vi.fn() }));

const IDLE: WorkStatus = { active: false, everCompleted: false, pending: false, running: false };
let workStatus: WorkStatus = { ...IDLE };
const statusOf = vi.fn((): WorkStatus => workStatus);
let epoch = 0;
const sessionEpoch = vi.fn((): number => epoch);
const runTaskResult = vi.fn();

const submitTask = vi.fn(runSpecWith(runTaskResult));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn(() => ({ cancelByType: vi.fn(() => vi.fn()), runTaskResult, sessionEpoch, statusOf, submitTask })),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({
    notifyError: mockNotifyError,
    notifyInfo: mockNotifyInfo,
    showErrorMessage: mockShowErrorMessage,
    showSuccessMessage: mockShowSuccessMessage,
  })),
}));

vi.mock('@/modules/auth/use-users-api', () => ({
  useUsersApi: vi.fn(() => ({
    colibriLogout: mockColibriLogout,
  })),
}));

vi.mock('@/modules/session/api/use-sync-api', () => ({
  useSyncApi: vi.fn(() => ({
    forceSync: mockForceSync,
  })),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => ref<string>('%Y-%m-%d %H:%M:%S')),
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
    mockColibriLogout.mockResolvedValue(true);
    workStatus = { ...IDLE };
    epoch = 0;
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
      runTaskResult.mockResolvedValue(ok(true));
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

    it('should show a message that outlasts the logout on a successful download sync', async () => {
      set(sync.syncAction, SYNC_DOWNLOAD);
      runTaskResult.mockResolvedValue(ok(true));
      const logout = vi.fn(async (): Promise<void> => {});

      await sync.forceSync(logout);

      expect(mockShowSuccessMessage).toHaveBeenCalledOnce();
      expect(mockNotifyInfo).not.toHaveBeenCalled();
      expect(logout).toHaveBeenCalledOnce();
    });

    it('should say which backup a download restored', async () => {
      set(sync.syncAction, SYNC_DOWNLOAD);
      runTaskResult.mockResolvedValue(ok({ lastModifyTs: 1760882400 }));
      const logout = vi.fn(async (): Promise<void> => {});

      await sync.forceSync(logout);

      expect(mockShowSuccessMessage).toHaveBeenCalledExactlyOnceWith(
        'actions.session.force_sync.success.title',
        'actions.session.force_sync.success.message_download::2025-10-19 14:00:00', // vitest runs in UTC
      );
      expect(logout).toHaveBeenCalledOnce();
    });

    it('should use the generic message for a restored backup in the old format', async () => {
      set(sync.syncAction, SYNC_DOWNLOAD);
      runTaskResult.mockResolvedValue(ok({ lastModifyTs: null }));
      const logout = vi.fn(async (): Promise<void> => {});

      await sync.forceSync(logout);

      expect(mockShowSuccessMessage).toHaveBeenCalledExactlyOnceWith(
        'actions.session.force_sync.success.title',
        'actions.session.force_sync.success.message',
      );
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

    it('should notify a failure on an actionable upload task failure', async () => {
      set(sync.syncAction, SYNC_UPLOAD);
      runTaskResult.mockResolvedValue(err(TaskFailed({ message: 'boom' })));

      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(mockNotifyError).toHaveBeenCalledExactlyOnceWith(
        'actions.session.force_sync.error.title',
        'actions.session.force_sync.error.message::boom',
      );
    });

    it('should stay silent on a cancelled upload task', async () => {
      set(sync.syncAction, SYNC_UPLOAD);
      runTaskResult.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(mockNotifyError).not.toHaveBeenCalled();
      expect(mockNotifyInfo).not.toHaveBeenCalled();
    });

    it('should not lock colibri for an upload, and keep it cancellable', async () => {
      set(sync.syncAction, SYNC_UPLOAD);
      runTaskResult.mockResolvedValue(ok(true));

      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(mockColibriLogout).not.toHaveBeenCalled();
      expect(submitTask.mock.calls[0][0]).toMatchObject({ interruptible: true });
    });
  });

  // Colibri is locked before the db is replaced, and only a login unlocks it, so a locked download logs out
  describe('forceSync download', () => {
    it('should not be cancellable once running', async () => {
      runTaskResult.mockResolvedValue(ok(true));

      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(submitTask.mock.calls[0][0]).toMatchObject({ interruptible: false });
    });

    it('should lock colibri before starting the backend task', async () => {
      runTaskResult.mockResolvedValue(ok(true));

      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(mockColibriLogout).toHaveBeenCalledOnce();
      expect(mockColibriLogout.mock.invocationCallOrder[0]).toBeLessThan(runTaskResult.mock.invocationCallOrder[0]);
    });

    it('should not download, and keep the session, when colibri can not be locked', async () => {
      mockColibriLogout.mockRejectedValue(new Error('colibri down'));
      const logout = vi.fn(async (): Promise<void> => {});

      await sync.forceSync(logout);

      expect(runTaskResult).not.toHaveBeenCalled();
      expect(mockNotifyError).toHaveBeenCalledExactlyOnceWith(
        'actions.session.force_sync.error.title',
        'actions.session.force_sync.error.message::colibri down',
      );
      expect(logout).not.toHaveBeenCalled();
    });

    it('should show an actionable failure and log out', async () => {
      runTaskResult.mockResolvedValue(err(TaskFailed({ message: 'boom' })));
      const logout = vi.fn(async (): Promise<void> => {});

      await sync.forceSync(logout);

      expect(mockShowErrorMessage).toHaveBeenCalledExactlyOnceWith(
        'actions.session.force_sync.error.title',
        'actions.session.force_sync.error.message::boom',
      );
      expect(logout).toHaveBeenCalledOnce();
    });

    it('should log out when the backend ended the task, as colibri is locked', async () => {
      runTaskResult.mockResolvedValue(err(BackendCancelled({ message: 'backend gone' })));
      const logout = vi.fn(async (): Promise<void> => {});

      await sync.forceSync(logout);

      expect(mockShowErrorMessage).toHaveBeenCalledExactlyOnceWith(
        'actions.session.force_sync.error.title',
        'actions.session.force_sync.error.message::backend gone',
      );
      expect(logout).toHaveBeenCalledOnce();
    });

    it('should leave colibri and the session alone when dropped before running', async () => {
      submitTask.mockResolvedValueOnce(err(Cancelled({ message: 'Cancelled before running' })));
      const logout = vi.fn(async (): Promise<void> => {});

      await sync.forceSync(logout);

      expect(mockColibriLogout).not.toHaveBeenCalled();
      expect(mockShowErrorMessage).not.toHaveBeenCalled();
      expect(mockNotifyError).not.toHaveBeenCalled();
      expect(logout).not.toHaveBeenCalled();
    });

    it('should not log out again when the session ended during the download', async () => {
      runTaskResult.mockImplementation(async () => {
        epoch++;
        return err(Cancelled({ message: 'session ended' }));
      });
      const logout = vi.fn(async (): Promise<void> => {});

      await sync.forceSync(logout);

      expect(mockColibriLogout).toHaveBeenCalledOnce();
      expect(mockShowErrorMessage).not.toHaveBeenCalled();
      expect(logout).not.toHaveBeenCalled();
    });
  });
});
