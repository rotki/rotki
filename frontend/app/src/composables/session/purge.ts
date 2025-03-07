import type { TaskMeta } from '@/types/task';
import { useSessionApi } from '@/composables/api/session';
import { useHistoryStore } from '@/store/history';
import { useNotificationsStore } from '@/store/notifications';
import { useStatusStore } from '@/store/status';
import { useTaskStore } from '@/store/tasks';
import { Purgeable } from '@/types/session/purge';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';

interface UseSessionPurge {
  purgeCache: (purgeable: Purgeable, value: string) => void;
  refreshGeneralCache: (source: string) => Promise<void>;
}

export function useSessionPurge(): UseSessionPurge {
  const { refreshGeneralCacheTask } = useSessionApi();
  const { resetStatus } = useStatusStore();
  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { resetProtocolCacheUpdatesStatus } = useHistoryStore();
  const { t } = useI18n();

  const purgeExchange = (): void => {
    resetStatus(Section.TRADES);
    resetStatus(Section.ASSET_MOVEMENT);
  };

  const purgeTransactions = (): void => {
    resetStatus(Section.HISTORY_EVENT);
  };

  const purgeCache = (purgeable: Purgeable, value: string): void => {
    if (purgeable === Purgeable.CENTRALIZED_EXCHANGES) {
      if (!value)
        purgeExchange();
    }
    else if (purgeable === Purgeable.TRANSACTIONS) {
      purgeTransactions();
    }
  };

  const refreshGeneralCache = async (source: string): Promise<void> => {
    resetProtocolCacheUpdatesStatus();
    const taskType = TaskType.REFRESH_GENERAL_CACHE;
    const { taskId } = await refreshGeneralCacheTask(source);
    try {
      await awaitTask<boolean, TaskMeta>(taskId, taskType, {
        title: t('actions.session.refresh_general_cache.task.title', { name: source }),
      });
    }
    catch (error: any) {
      if (isTaskCancelled(error)) {
        return;
      }
      notify({
        display: true,
        message: t('actions.session.refresh_general_cache.error.message', {
          message: error.message,
          name: source,
        }),
        title: t('actions.session.refresh_general_cache.task.title', { name: source }),
      });
    }
  };

  return {
    purgeCache,
    refreshGeneralCache,
  };
}
