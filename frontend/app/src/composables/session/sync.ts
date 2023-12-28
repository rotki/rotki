import { Severity } from '@rotki/common/lib/messages';
import { api } from '@/services/rotkehlchen-api';
import { type TaskMeta, UserCancelledTaskError } from '@/types/task';
import { TaskType } from '@/types/task-type';
import {
  SYNC_DOWNLOAD,
  SYNC_UPLOAD,
  type SyncAction
} from '@/types/session/sync';

export const useSync = createSharedComposable(() => {
  const { isTaskRunning, awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { t } = useI18n();
  const syncAction = ref<SyncAction>(SYNC_DOWNLOAD);
  const displaySyncConfirmation = ref(false);
  const confirmChecked = ref(false);

  const showSyncConfirmation = (action: SyncAction) => {
    set(syncAction, action);
    set(displaySyncConfirmation, true);
  };

  const cancelSync = () => {
    set(displaySyncConfirmation, false);
    set(confirmChecked, false);
  };

  const forceSync = async (logout: () => Promise<void>): Promise<void> => {
    const taskType = TaskType.FORCE_SYNC;
    if (get(isTaskRunning(taskType))) {
      return;
    }

    const notifyFailure = (error: string): void => {
      const title = t('actions.session.force_sync.error.title');
      const message = t('actions.session.force_sync.error.message', {
        error
      });

      notify({
        title,
        message,
        display: true
      });
    };

    try {
      api.cancel();
      const action = get(syncAction);
      if (action === SYNC_UPLOAD) {
        set(displaySyncConfirmation, false);
      }
      const { taskId } = await useSyncApi().forceSync(action);
      const { result, message } = await awaitTask<boolean, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.session.force_sync.task.title')
        }
      );

      if (result) {
        const title = t('actions.session.force_sync.success.title');
        const message = t('actions.session.force_sync.success.message');

        notify({
          title,
          message,
          severity: Severity.INFO,
          display: true
        });

        if (action === SYNC_DOWNLOAD) {
          await logout();
        }
      } else {
        notifyFailure(message ?? '');
      }
    } catch (e: any) {
      if (!(e instanceof UserCancelledTaskError)) {
        notifyFailure(e.message);
      }
    }
  };

  return {
    syncAction,
    confirmChecked,
    displaySyncConfirmation,
    forceSync,
    cancelSync,
    showSyncConfirmation
  };
});
