import type { DatabaseUploadProgress, DbUploadResult } from '@/modules/core/messaging/types';
import type { TaskMeta } from '@/modules/core/tasks/types';
import { api } from '@/modules/core/api/rotki-api';
import { serializer } from '@/modules/core/messaging/use-dynamic-messages';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import { useSyncApi } from '@/modules/session/api/use-sync-api';
import { SYNC_DOWNLOAD, SYNC_UPLOAD, type SyncAction } from '@/modules/session/sync';

export const useSync = createSharedComposable(() => {
  const { runTask } = useTaskHandler();
  const { isTaskRunning } = useTaskStore();
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
    if (isTaskRunning(TaskType.FORCE_SYNC))
      return;

    const notifyFailure = (error: string): void => {
      const title = t('actions.session.force_sync.error.title');
      const message = t('actions.session.force_sync.error.message', { error });

      notifyError(title, message);
    };

    api.cancelAllQueued();
    api.cancel();
    const action = get(syncAction);
    if (action === SYNC_UPLOAD)
      set(displaySyncConfirmation, false);

    const outcome = await runTask<boolean, TaskMeta>(
      async () => useSyncApi().forceSync(action),
      { type: TaskType.FORCE_SYNC, meta: { title: t('actions.session.force_sync.task.title') }, guard: false },
    );

    if (outcome.success) {
      if (outcome.result) {
        const title = t('actions.session.force_sync.success.title');
        const message = t('actions.session.force_sync.success.message');

        notifyInfo(title, message);

        if (action === SYNC_DOWNLOAD)
          await logout();
      }
      else {
        notifyFailure(outcome.message ?? '');
      }
    }
    else if (isActionableFailure(outcome)) {
      notifyFailure(outcome.message);
    }
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
