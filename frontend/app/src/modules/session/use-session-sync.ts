import type { DatabaseUploadProgress, DbUploadResult } from '@/modules/core/messaging/types';
import { err, isErr, type Result } from 'plainfp/result';
import { hasTag } from 'plainfp/tagged';
import { useUsersApi } from '@/modules/auth/use-users-api';
import { api } from '@/modules/core/api/rotki-api';
import { displayDateFormatter } from '@/modules/core/common/date-formatter';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { serializer } from '@/modules/core/messaging/use-dynamic-messages';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useSyncApi } from '@/modules/session/api/use-sync-api';
import { SYNC_DOWNLOAD, SYNC_UPLOAD, type SyncAction } from '@/modules/session/sync';
import { useSetting } from '@/modules/settings/use-setting';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

/**
 * A successful download carries the authenticated last write timestamp of the restored backup,
 * null for a backup in the old format. A successful upload is a plain true. A failure is always
 * a task error that carries the reason.
 */
type ForceSyncResult = true | { lastModifyTs: number | null };

/** A cancellation is silent as a toast, but still needs explaining when the download logs out */
type SyncOutcome =
  | { kind: 'success'; message: string }
  | { kind: 'failure'; error: string }
  | { kind: 'silent'; error: string };

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
  const { sessionEpoch, statusOf, submitTask } = useNativeTask();
  const { notifyError, notifyInfo, showErrorMessage, showSuccessMessage } = useNotifications();
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

  const failureMessage = (error: string): string => t('actions.session.force_sync.error.message', { error });

  const describeOutcome = (outcome: Result<ForceSyncResult, TaskError>): SyncOutcome => {
    if (isErr(outcome)) {
      const { error } = outcome;
      return isActionable(error) ? { error: error.message, kind: 'failure' } : { error: error.message, kind: 'silent' };
    }
    return { kind: 'success', message: successMessage(outcome.value) };
  };

  /**
   * Colibri stays locked after a download and only a login unlocks it again, so a download that
   * locked it ends in a logout, whatever its outcome. A toast would vanish on it; the message
   * dialog stays open on the login screen. Logout resets every store, the message store and the
   * date display setting included, so the text is built before it and shown once it is done.
   */
  const finishDownload = async (outcome: Result<ForceSyncResult, TaskError>, logout: () => Promise<void>): Promise<void> => {
    const described = describeOutcome(outcome);
    await logout();

    if (described.kind === 'success')
      showSuccessMessage(t('actions.session.force_sync.success.title'), described.message);
    else
      showErrorMessage(t('actions.session.force_sync.error.title'), failureMessage(described.error));
  };

  const notifyOutcome = (outcome: Result<ForceSyncResult, TaskError>): void => {
    const described = describeOutcome(outcome);
    if (described.kind === 'success')
      notifyInfo(t('actions.session.force_sync.success.title'), described.message);
    else if (described.kind === 'failure')
      notifyError(t('actions.session.force_sync.error.title'), failureMessage(described.error));
  };

  const forceSync = async (logout: () => Promise<void>): Promise<void> => {
    if (statusOf(ActivityKind.SYNC).active)
      return;

    api.cancelAllQueued();
    api.cancel();
    const action = get(syncAction);
    if (action === SYNC_UPLOAD)
      set(displaySyncConfirmation, false);

    const epoch = sessionEpoch();
    const outcome = await submitTask<ForceSyncResult>({
      id: makeActivityId(ActivityKind.SYNC),
      // A download replaces the user db file, and core must not be stopped half way through.
      interruptible: action === SYNC_UPLOAD,
      kind: ActivityKind.SYNC,
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
      title: t('task_center.group.sync'),
    });

    // A session that ended meanwhile was already logged out, which locked colibri as well
    if (action === SYNC_DOWNLOAD && lockedColibri(outcome) && sessionEpoch() === epoch)
      await finishDownload(outcome, logout);
    else
      notifyOutcome(outcome);
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
    showSyncConfirmation,
    syncAction,
    uploadProgress,
    uploadStatus,
    uploadStatusAlreadyHandled,
  };
});
