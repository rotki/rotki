import type { DatabaseUploadProgress, DbUploadResult } from '@/modules/core/messaging/types';
import { err, flatMap, isErr, ok, type Result } from 'plainfp/result';
import { api } from '@/modules/core/api/rotki-api';
import { serializer } from '@/modules/core/messaging/use-dynamic-messages';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useSyncApi } from '@/modules/session/api/use-sync-api';
import { SYNC_DOWNLOAD, SYNC_UPLOAD, type SyncAction } from '@/modules/session/sync';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

export const useSync = createSharedComposable(() => {
  const { statusOf, submitTask } = useNativeTask();
  const { notifyInfo } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });
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

  const forceSync = async (logout: () => Promise<void>): Promise<void> => {
    if (statusOf(ActivityKind.SYNC).active)
      return;

    api.cancelAllQueued();
    api.cancel();
    const action = get(syncAction);
    if (action === SYNC_UPLOAD)
      set(displaySyncConfirmation, false);

    set(manualSyncActive, true);
    const outcome = await submitTask<boolean>({
      id: makeActivityId(ActivityKind.SYNC),
      kind: ActivityKind.SYNC,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<boolean, TaskError>> => flatMap(
        await runTask<boolean>(
          async () => useSyncApi().forceSync(action),
        ),
        (synced): Result<boolean, TaskError> => (synced
          ? ok(true)
          : err(TaskFailed({ message: t('sync_indicator.activity.refused') }))),
      ),
      subtitle: action === SYNC_UPLOAD ? t('sync_indicator.activity.upload') : t('sync_indicator.activity.download'),
      title: t('task_center.group.sync'),
    }).finally(() => set(manualSyncActive, false));

    // The dock row reports failures, refusals and finished backups.
    if (isErr(outcome) || action !== SYNC_DOWNLOAD)
      return;

    // A restore replaces this database and logs out, taking the dock with it, so it says so first.
    notifyInfo(t('actions.session.force_sync.success.title'), t('actions.session.force_sync.success.message'));
    await logout();
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
