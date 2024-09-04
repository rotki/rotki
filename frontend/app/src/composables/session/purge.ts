import { Purgeable } from '@/types/session/purge';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import type { Module } from '@/types/modules';
import type { TaskMeta } from '@/types/task';

interface UseSessionPurge {
  purgeCache: (purgeable: Purgeable, value: string) => void;
  refreshGeneralCache: () => Promise<void>;
}

export function useSessionPurge(): UseSessionPurge {
  const { resetState } = useDefiStore();
  const { refreshGeneralCacheTask } = useSessionApi();
  const { resetStatus } = useStatusStore();

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
    else if (purgeable === Purgeable.DECENTRALIZED_EXCHANGES) {
      resetState((value as Module) || Purgeable.DECENTRALIZED_EXCHANGES);
    }
    else if (purgeable === Purgeable.DEFI_MODULES) {
      resetState((value as Module) || Purgeable.DEFI_MODULES);
    }
    else if (purgeable === Purgeable.TRANSACTIONS) {
      purgeTransactions();
    }
  };

  const { awaitTask } = useTaskStore();
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const { resetProtocolCacheUpdatesStatus } = useHistoryStore();
  const refreshGeneralCache = async (): Promise<void> => {
    resetProtocolCacheUpdatesStatus();
    const taskType = TaskType.REFRESH_GENERAL_CACHE;
    const { taskId } = await refreshGeneralCacheTask();
    try {
      await awaitTask<boolean, TaskMeta>(taskId, taskType, {
        title: t('actions.session.refresh_general_cache.task.title'),
      });
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        notify({
          title: t('actions.session.refresh_general_cache.task.title'),
          message: t('actions.session.refresh_general_cache.error.message', {
            message: error.message,
          }),
          display: true,
        });
      }
    }
  };

  return {
    purgeCache,
    refreshGeneralCache,
  };
}
