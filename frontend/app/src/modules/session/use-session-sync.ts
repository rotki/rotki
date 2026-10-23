import type { DatabaseUploadProgress, DbUploadResult } from '@/modules/core/messaging/types';
import { err, isErr, type Result } from 'plainfp/result';
import { hasTag } from 'plainfp/tagged';
import { useUsersApi } from '@/modules/auth/use-users-api';
import { api } from '@/modules/core/api/rotki-api';
import { displayDateFormatter } from '@/modules/core/common/date-formatter';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { serializer } from '@/modules/core/messaging/use-dynamic-messages';
import { captureSession } from '@/modules/core/session/session-lifecycle';
import { isActionable, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useSyncApi } from '@/modules/session/api/use-sync-api';
import { manualSyncActivity } from '@/modules/session/session.activity';
import { SYNC_DOWNLOAD, SYNC_UPLOAD, type SyncAction } from '@/modules/session/sync';
import { type RestoreOutcome, RestoreOutcomeKind, useRestoreOutcomeNotice } from '@/modules/session/use-restore-outcome-notice';
import { useSetting } from '@/modules/settings/use-setting';
import { useNativeTask } from '@/modules/task-center/use-native-task';

/**
 * A successful download carries the authenticated last write timestamp of the restored backup,
 * null for a backup in the old format. A successful upload is a plain true. A failure is always
 * a task error that carries the reason.
 */
type ForceSyncResult = true | { lastModifyTs: number | null };

/** Colibri could not be locked, so the download never started */
class ColibriLockError extends Error {
  override name = 'ColibriLockError';
}

/**
 * Whether the download got as far as locking colibri, which it only does once it runs, so a
 * download dropped from the queue leaves colibri alone. Otherwise a running download is only
 * cancelled when the session ends.
 */
function lockedColibri(outcome: Result<ForceSyncResult, TaskError>): boolean {
  if (!isErr(outcome))
    return true;
  const { error } = outcome;
  return !hasTag(error, 'Cancelled') && !(isActionable(error) && error.cause instanceof ColibriLockError);
}

export const useSync = createSharedComposable(() => {
  const { statusOf, submitTask } = useNativeTask();
  const { show: showRestoreOutcome } = useRestoreOutcomeNotice();
  const { colibriLogout } = useUsersApi();
  const { t } = useI18n({ useScope: 'global' });
  const dateDisplayFormat = useSetting('dateDisplayFormat');
  const syncAction = ref<SyncAction>(SYNC_DOWNLOAD);
  const displaySyncConfirmation = ref(false);
  const confirmChecked = ref(false);
  const uploadStatus = useSessionStorage<DbUploadResult | null>('rotki.upload_status.message', null, {
    serializer,
  });
  const uploadStatusAlreadyHandled = useSessionStorage<boolean>('rotki.upload_status.handled', false);
  const uploadProgress = ref<DatabaseUploadProgress>();
  /**
   * Whether a sync the user started is running, so upload progress feeds its row and an
   * automatic backup is not opened beside it.
   */
  const manualSyncActive = ref<boolean>(false);

  const showSyncConfirmation = (action: SyncAction): void => {
    set(syncAction, action);
    set(displaySyncConfirmation, true);
  };

  const cancelSync = (): void => {
    set(displaySyncConfirmation, false);
    set(confirmChecked, false);
  };

  /** A forced download skips the "remote is newer" check, so say which backup was restored */
  const successMessage = (result: ForceSyncResult): string => {
    if (typeof result === 'object' && typeof result.lastModifyTs === 'number') {
      const date = displayDateFormatter.format(new Date(result.lastModifyTs * 1000), get(dateDisplayFormat));
      return t('actions.session.force_sync.success.message_download', { date });
    }
    return t('actions.session.force_sync.success.message');
  };

  /**
   * Colibri stays locked after a download and only a login unlocks it again, so a download that
   * locked it ends in a logout, whatever its outcome. The logout takes the dock row with it, so
   * the outcome goes to a notice on the login screen. The logout resets the date display
   * setting, so the text is built before it.
   */
  const finishDownload = async (outcome: Result<ForceSyncResult, TaskError>, logout: () => Promise<void>): Promise<void> => {
    const restoreOutcome: RestoreOutcome = isErr(outcome)
      ? {
          kind: RestoreOutcomeKind.FAILED,
          message: t('actions.session.force_sync.error.message', { error: outcome.error.message }),
        }
      : { kind: RestoreOutcomeKind.RESTORED, message: successMessage(outcome.value) };
    await logout();
    showRestoreOutcome(restoreOutcome);
  };

  /**
   * Runs the sync the user confirmed. Its dock row reports an upload's outcome, and a download's
   * when it failed before locking colibri; a download that locked it ends in {@link finishDownload}.
   */
  const forceSync = async (logout: () => Promise<void>): Promise<void> => {
    if (statusOf(manualSyncActivity.kind).active)
      return;

    api.cancelAllQueued();
    api.cancel();
    const action = get(syncAction);
    if (action === SYNC_UPLOAD)
      set(displaySyncConfirmation, false);

    set(manualSyncActive, true);
    const sameSessionLive = captureSession();
    const outcome = await submitTask<ForceSyncResult>({
      id: manualSyncActivity.id(),
      // A download replaces the user db file, and core must not be stopped half way through.
      interruptible: action === SYNC_UPLOAD,
      kind: manualSyncActivity.kind,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<ForceSyncResult, TaskError>> => {
        if (action === SYNC_DOWNLOAD) {
          // Colibri's own connection to the user db would corrupt the file core restores under it
          try {
            await colibriLogout();
          }
          catch (error: unknown) {
            const message = getErrorMessage(error);
            return err(TaskFailed({ cause: new ColibriLockError(message, { cause: error }), message }));
          }
        }
        return runTask<ForceSyncResult>(async () => useSyncApi().forceSync(action));
      },
      subtitle: action === SYNC_UPLOAD ? t('sync_indicator.activity.upload') : t('sync_indicator.activity.download'),
      title: t('task_center.group.sync'),
    }).finally(() => set(manualSyncActive, false));

    // A session that ended meanwhile was already logged out, which locked colibri as well
    if (action === SYNC_DOWNLOAD && lockedColibri(outcome) && sameSessionLive())
      await finishDownload(outcome, logout);
  };

  const clearUploadStatus = (): void => {
    set(uploadStatus, null);
    set(uploadProgress, undefined);
  };

  return {
    cancelSync,
    clearUploadStatus,
    confirmChecked,
    displaySyncConfirmation,
    forceSync,
    manualSyncActive,
    showSyncConfirmation,
    syncAction,
    uploadProgress,
    uploadStatus,
    uploadStatusAlreadyHandled,
  };
});
