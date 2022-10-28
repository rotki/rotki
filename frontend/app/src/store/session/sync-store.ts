import { Severity } from '@rotki/common/lib/messages';
import { MaybeRef } from '@vueuse/core';
import { balanceKeys } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { SYNC_DOWNLOAD, SyncAction } from '@/services/types-api';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

export const useSyncStoreStore = defineStore('syncStore', () => {
  const { isTaskRunning, awaitTask } = useTasks();
  const { notify } = useNotifications();
  const { tc } = useI18n();

  async function forceSync(
    action: MaybeRef<SyncAction>,
    logout: () => Promise<void>
  ): Promise<void> {
    const taskType = TaskType.FORCE_SYNC;
    if (get(isTaskRunning(taskType))) {
      return;
    }

    function notifyFailure(error: string): void {
      const title = tc('actions.session.force_sync.error.title');
      const message = tc('actions.session.force_sync.error.message', 0, {
        error
      });

      notify({
        title,
        message,
        display: true
      });
    }

    try {
      const { taskId } = await api.forceSync(get(action));
      const { result, message } = await awaitTask<boolean, TaskMeta>(
        taskId,
        taskType,
        {
          title: tc('actions.session.force_sync.task.title'),
          numericKeys: balanceKeys
        }
      );

      if (result) {
        const title = tc('actions.session.force_sync.success.title');
        const message = tc('actions.session.force_sync.success.message');

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
      notifyFailure(e.message);
    }
  }
  return {
    forceSync
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useSyncStoreStore, import.meta.hot));
}
