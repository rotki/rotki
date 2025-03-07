import type { TaskMeta } from '@/types/task';
import type { DbUploadResult } from '@/types/websocket-messages';
import { useSyncApi } from '@/composables/api/session/sync';
import { serializer } from '@/composables/dynamic-messages';
import { api } from '@/services/rotkehlchen-api';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { SYNC_DOWNLOAD, SYNC_UPLOAD, type SyncAction } from '@/types/session/sync';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { Severity } from '@rotki/common';

export const useSync = createSharedComposable(() => {
  const { awaitTask, isTaskRunning } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { t } = useI18n();
  const syncAction = ref<SyncAction>(SYNC_DOWNLOAD);
  const displaySyncConfirmation = ref(false);
  const confirmChecked = ref(false);
  const uploadStatus = useSessionStorage<DbUploadResult>('rotki.upload_status.message', null, {
    serializer,
  });
  const uploadStatusAlreadyHandled = useSessionStorage<boolean>('rotki.upload_status.handled', false);

  const showSyncConfirmation = (action: SyncAction): void => {
    set(syncAction, action);
    set(displaySyncConfirmation, true);
  };

  const cancelSync = (): void => {
    set(displaySyncConfirmation, false);
    set(confirmChecked, false);
  };

  const forceSync = async (logout: () => Promise<void>): Promise<void> => {
    const taskType = TaskType.FORCE_SYNC;
    if (get(isTaskRunning(taskType)))
      return;

    const notifyFailure = (error: string): void => {
      const title = t('actions.session.force_sync.error.title');
      const message = t('actions.session.force_sync.error.message', {
        error,
      });

      notify({
        display: true,
        message,
        title,
      });
    };

    try {
      api.cancel();
      const action = get(syncAction);
      if (action === SYNC_UPLOAD)
        set(displaySyncConfirmation, false);

      const { taskId } = await useSyncApi().forceSync(action);
      const { message, result } = await awaitTask<boolean, TaskMeta>(taskId, taskType, {
        title: t('actions.session.force_sync.task.title'),
      });

      if (result) {
        const title = t('actions.session.force_sync.success.title');
        const message = t('actions.session.force_sync.success.message');

        notify({
          display: true,
          message,
          severity: Severity.INFO,
          title,
        });

        if (action === SYNC_DOWNLOAD)
          await logout();
      }
      else {
        notifyFailure(message ?? '');
      }
    }
    catch (error: any) {
      if (!isTaskCancelled(error))
        notifyFailure(error.message);
    }
  };

  const clearUploadStatus = (): void => {
    set(uploadStatus, null);
  };

  return {
    cancelSync,
    clearUploadStatus,
    confirmChecked,
    displaySyncConfirmation,
    forceSync,
    showSyncConfirmation,
    syncAction,
    uploadStatus,
    uploadStatusAlreadyHandled,
  };
});
