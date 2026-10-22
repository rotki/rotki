import type { RotkiApi } from '@/modules/core/api/rotki-api';
import type { WorkStatus } from '@/modules/task-center/core/types';
import { createMock } from '@test/utils/create-mock';
import { runSpecWith } from '@test/utils/mocks/native-task';
import { err, ok } from 'plainfp/result';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { beginSession, endSession } from '@/modules/core/session/session-lifecycle';
import { BackendCancelled, Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { SYNC_DOWNLOAD, SYNC_UPLOAD } from '@/modules/session/sync';
import { RestoreOutcomeKind, useRestoreOutcomeNotice } from '@/modules/session/use-restore-outcome-notice';
import { useSync } from '@/modules/session/use-session-sync';

const mockColibriLogout = vi.fn<() => Promise<boolean>>();
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

/** Runs the sync and collects what its task returned, which is what the dock row reports. */
async function forceSyncCollectingOutcome(sync: ReturnType<typeof useSync>, logout: () => Promise<void>): Promise<unknown[]> {
  const outcomes: unknown[] = [];
  submitTask.mockImplementationOnce(async (spec) => {
    const outcome = await spec.run({ cancelled: () => false, report: () => {}, runTask: runTaskResult });
    outcomes.push(outcome);
    return outcome;
  });
  await sync.forceSync(logout);
  return outcomes;
}

function restoreOutcome(): ReturnType<typeof useRestoreOutcomeNotice>['outcome']['value'] {
  return get(useRestoreOutcomeNotice().outcome);
}

describe('useSync', () => {
  let sync: ReturnType<typeof useSync>;

  beforeAll(() => {
    setActivePinia(createPinia());
  });

  beforeEach(() => {
    vi.clearAllMocks();
    mockColibriLogout.mockResolvedValue(true);
    workStatus = { ...IDLE };
    useRestoreOutcomeNotice().dismiss();
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

    it('should mark a manual sync active while it runs', async () => {
      const seen: boolean[] = [];
      runTaskResult.mockImplementationOnce(async () => {
        seen.push(get(sync.manualSyncActive));
        return ok(true);
      });
      set(sync.syncAction, SYNC_UPLOAD);

      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(seen).toEqual([true]);
      expect(get(sync.manualSyncActive)).toBe(false);
    });
  });

  describe('forceSync upload', () => {
    beforeEach(() => {
      set(sync.syncAction, SYNC_UPLOAD);
    });

    it('should close the confirmation dialog before an upload sync', async () => {
      set(sync.displaySyncConfirmation, true);
      runTaskResult.mockResolvedValue(ok(true));

      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(get(sync.displaySyncConfirmation)).toBe(false);
    });

    it('should leave a successful upload to its dock row and keep the session', async () => {
      runTaskResult.mockResolvedValue(ok(true));
      const logout = vi.fn(async (): Promise<void> => {});

      const outcomes = await forceSyncCollectingOutcome(sync, logout);

      expect(outcomes).toEqual([expect.objectContaining({ ok: true })]);
      expect(restoreOutcome()).toBeUndefined();
      expect(logout).not.toHaveBeenCalled();
    });

    it('should leave a failed upload to its dock row and keep the session', async () => {
      runTaskResult.mockResolvedValue(err(TaskFailed({ message: 'boom' })));
      const logout = vi.fn(async (): Promise<void> => {});

      const outcomes = await forceSyncCollectingOutcome(sync, logout);

      expect(outcomes).toEqual([expect.objectContaining({ ok: false })]);
      expect(restoreOutcome()).toBeUndefined();
      expect(logout).not.toHaveBeenCalled();
    });

    it('should not lock colibri for an upload, and keep it cancellable', async () => {
      runTaskResult.mockResolvedValue(ok(true));

      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(mockColibriLogout).not.toHaveBeenCalled();
      expect(submitTask.mock.calls[0][0]).toMatchObject({ interruptible: true });
    });
  });

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

    it('should leave the outcome for the login screen only once the logout is done', async () => {
      runTaskResult.mockResolvedValue(ok(true));
      let outcomeDuringLogout: unknown = 'not logged out';
      const logout = vi.fn(async (): Promise<void> => {
        outcomeDuringLogout = restoreOutcome();
      });

      await sync.forceSync(logout);

      expect(logout).toHaveBeenCalledOnce();
      expect(outcomeDuringLogout).toBeUndefined();
      expect(restoreOutcome()).toEqual({
        kind: RestoreOutcomeKind.RESTORED,
        message: 'actions.session.force_sync.success.message',
      });
    });

    it('should say which backup a download restored', async () => {
      runTaskResult.mockResolvedValue(ok({ lastModifyTs: 1760882400 }));

      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(restoreOutcome()).toEqual({
        kind: RestoreOutcomeKind.RESTORED,
        message: 'actions.session.force_sync.success.message_download::2025-10-19 14:00:00', // vitest runs in UTC
      });
    });

    it('should use the generic message for a restored backup in the old format', async () => {
      runTaskResult.mockResolvedValue(ok({ lastModifyTs: null }));

      await sync.forceSync(vi.fn(async (): Promise<void> => {}));

      expect(restoreOutcome()).toEqual({
        kind: RestoreOutcomeKind.RESTORED,
        message: 'actions.session.force_sync.success.message',
      });
    });

    it('should leave a download colibri could not be locked for to its dock row, and keep the session', async () => {
      mockColibriLogout.mockRejectedValue(new Error('colibri down'));
      const logout = vi.fn(async (): Promise<void> => {});

      const outcomes = await forceSyncCollectingOutcome(sync, logout);

      expect(runTaskResult).not.toHaveBeenCalled();
      expect(outcomes).toEqual([expect.objectContaining({ ok: false })]);
      expect(restoreOutcome()).toBeUndefined();
      expect(logout).not.toHaveBeenCalled();
    });

    it('should tell the login screen why a download failed after its logout', async () => {
      runTaskResult.mockResolvedValue(err(TaskFailed({ message: 'boom' })));
      const logout = vi.fn(async (): Promise<void> => {});

      await sync.forceSync(logout);

      expect(logout).toHaveBeenCalledOnce();
      expect(restoreOutcome()).toEqual({
        kind: RestoreOutcomeKind.FAILED,
        message: 'actions.session.force_sync.error.message::boom',
      });
    });

    it('should log out when the backend ended the task, as colibri is locked', async () => {
      runTaskResult.mockResolvedValue(err(BackendCancelled({ message: 'backend gone' })));
      const logout = vi.fn(async (): Promise<void> => {});

      await sync.forceSync(logout);

      expect(logout).toHaveBeenCalledOnce();
      expect(restoreOutcome()).toEqual({
        kind: RestoreOutcomeKind.FAILED,
        message: 'actions.session.force_sync.error.message::backend gone',
      });
    });

    it('should leave colibri and the session alone when dropped before running', async () => {
      submitTask.mockResolvedValueOnce(err(Cancelled({ message: 'Cancelled before running' })));
      const logout = vi.fn(async (): Promise<void> => {});

      await sync.forceSync(logout);

      expect(mockColibriLogout).not.toHaveBeenCalled();
      expect(restoreOutcome()).toBeUndefined();
      expect(logout).not.toHaveBeenCalled();
    });

    it('should not log out a later session when the session that locked colibri ended during the download', async () => {
      runTaskResult.mockImplementation(async () => {
        endSession();
        beginSession();
        return err(TaskFailed({ message: 'backend gone' }));
      });
      const logout = vi.fn(async (): Promise<void> => {});

      await sync.forceSync(logout);

      expect(mockColibriLogout).toHaveBeenCalledOnce();
      expect(restoreOutcome()).toBeUndefined();
      expect(logout).not.toHaveBeenCalled();
    });
  });
});
