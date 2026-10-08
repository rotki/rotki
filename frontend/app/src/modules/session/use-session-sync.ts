import type { DatabaseUploadProgress, DbUploadResult } from '@/modules/core/messaging/types';
import type { TaskError } from '@/modules/core/tasks/task-result';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { api } from '@/modules/core/api/rotki-api';
import { serializer } from '@/modules/core/messaging/use-dynamic-messages';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { useSyncApi } from '@/modules/session/api/use-sync-api';
import { SYNC_DOWNLOAD, SYNC_UPLOAD, type SyncAction } from '@/modules/session/sync';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

export const useSync = createSharedComposable(() => {
  const { statusOf, submitTask } = useNativeTask();
  const { notifyError, notifyInfo } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });
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

  const forceSync = async (logout: () => Promise<void>): Promise<void> => {
    if (statusOf(ActivityKind.SYNC).active)
      return;

    api.cancelAllQueued();
    api.cancel();
    const action = get(syncAction);
    if (action === SYNC_UPLOAD)
      set(displaySyncConfirmation, false);

    const outcome = await submitTask<boolean>({
      id: makeActivityId(ActivityKind.SYNC),
      kind: ActivityKind.SYNC,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<boolean, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => useSyncApi().forceSync(action),
        ),
        result => result,
      ),
      title: t('task_center.group.sync'),
    });

    if (isErr(outcome))
      return;

    if (!outcome.value) {
      notifyError(t('actions.session.force_sync.error.title'), t('actions.session.force_sync.error.message', { error: '' }));
      return;
    }

    notifyInfo(t('actions.session.force_sync.success.title'), t('actions.session.force_sync.success.message'));
    if (action === SYNC_DOWNLOAD)
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
    showSyncConfirmation,
    syncAction,
    uploadProgress,
    uploadStatus,
    uploadStatusAlreadyHandled,
  };
});
