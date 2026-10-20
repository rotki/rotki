import type { DatabaseUploadProgress, DbUploadResult } from '@/modules/core/messaging/types';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { useUsersApi } from '@/modules/auth/use-users-api';
import { api } from '@/modules/core/api/rotki-api';
import { displayDateFormatter } from '@/modules/core/common/date-formatter';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { serializer } from '@/modules/core/messaging/use-dynamic-messages';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { useSyncApi } from '@/modules/session/api/use-sync-api';
import { SYNC_DOWNLOAD, SYNC_UPLOAD, type SyncAction } from '@/modules/session/sync';
import { useSetting } from '@/modules/settings/use-setting';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

/**
 * A successful download carries the authenticated last write timestamp of the restored backup,
 * null for a backup in the old format. An upload, or a failure, is a plain boolean.
 */
type ForceSyncResult = boolean | { lastModifyTs: number | null };

export const useSync = createSharedComposable(() => {
  const { statusOf, submitTask } = useNativeTask();
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
  const successMessage = (result: Exclude<ForceSyncResult, false>): string => {
    if (typeof result === 'object' && typeof result.lastModifyTs === 'number') {
      const date = displayDateFormatter.format(new Date(result.lastModifyTs * 1000), get(dateDisplayFormat));
      return t('actions.session.force_sync.success.message_download', { date });
    }
    return t('actions.session.force_sync.success.message');
  };

  const failureMessage = (error: string): string => t('actions.session.force_sync.error.message', { error });

  /**
   * A download replaces the user db file. Colibri keeps its own connection to that file while
   * unlocked, and writing a new file under it corrupts the restored db. Returns false, after
   * telling the user, if colibri could not be locked.
   */
  const lockColibri = async (): Promise<boolean> => {
    try {
      await colibriLogout();
      return true;
    }
    catch (error: unknown) {
      notifyError(t('actions.session.force_sync.error.title'), failureMessage(getErrorMessage(error)));
      return false;
    }
  };

  /** The success message, or the failure error. Neither for a cancelled task, which stays silent. */
  const describeOutcome = (outcome: Result<ForceSyncResult, TaskError>): { message?: string; error?: string } => {
    if (isErr(outcome))
      return isActionable(outcome.error) ? { error: outcome.error.message } : {};
    return outcome.value ? { message: successMessage(outcome.value) } : { error: '' };
  };

  /**
   * Colibri stays locked after a download and only a login unlocks it again, so a finished
   * download ends in a logout. A toast would vanish on it; the message dialog stays open on the
   * login screen. A cancelled download does not log out: core may still be replacing the db file.
   */
  const finishDownload = async (
    { error, message }: { message?: string; error?: string },
    logout: () => Promise<void>,
  ): Promise<void> => {
    if (message !== undefined)
      showSuccessMessage(t('actions.session.force_sync.success.title'), message);
    else if (error !== undefined)
      showErrorMessage(t('actions.session.force_sync.error.title'), failureMessage(error));

    if (message !== undefined || error !== undefined)
      await logout();
  };

  const finishUpload = ({ error, message }: { message?: string; error?: string }): void => {
    if (message !== undefined)
      notifyInfo(t('actions.session.force_sync.success.title'), message);
    else if (error !== undefined)
      notifyError(t('actions.session.force_sync.error.title'), failureMessage(error));
  };

  const forceSync = async (logout: () => Promise<void>): Promise<void> => {
    if (statusOf(ActivityKind.SYNC).active)
      return;

    api.cancelAllQueued();
    api.cancel();
    const action = get(syncAction);
    if (action === SYNC_UPLOAD)
      set(displaySyncConfirmation, false);
    else if (!(await lockColibri()))
      return;

    const outcome = await submitTask<ForceSyncResult>({
      id: makeActivityId(ActivityKind.SYNC),
      kind: ActivityKind.SYNC,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<ForceSyncResult, TaskError>> => mapResult(
        await runTask<ForceSyncResult>(
          async () => useSyncApi().forceSync(action),
        ),
        result => result,
      ),
      title: t('task_center.group.sync'),
    });

    if (action === SYNC_DOWNLOAD)
      await finishDownload(describeOutcome(outcome), logout);
    else
      finishUpload(describeOutcome(outcome));
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
