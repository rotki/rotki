import { Purgeable } from '@/types/session/purge';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { type TaskMeta } from '@/types/task';

export const useSessionPurge = () => {
  const { resetState } = useDefiStore();
  const { reset } = useStaking();

  const { refreshGeneralCacheTask } = useSessionApi();

  const purgeExchange = async (): Promise<void> => {
    const { resetStatus } = useStatusUpdater(Section.TRADES);
    resetStatus();
    resetStatus(Section.ASSET_MOVEMENT);
  };

  const purgeTransactions = async (): Promise<void> => {
    const { resetStatus } = useStatusUpdater(Section.HISTORY_EVENT);
    resetStatus();
  };

  const purgeCache = async (
    purgeable: Purgeable,
    value: string
  ): Promise<void> => {
    if (purgeable === Purgeable.CENTRALIZED_EXCHANGES) {
      if (!value) {
        await purgeExchange();
      }
    } else if (purgeable === Purgeable.DECENTRALIZED_EXCHANGES) {
      resetState((value as Module) || Purgeable.DECENTRALIZED_EXCHANGES);
    } else if (purgeable === Purgeable.DEFI_MODULES) {
      const isEth2 = value === Module.ETH2;
      reset(isEth2 ? value : undefined);
      resetState((value as Module) || Purgeable.DEFI_MODULES);
    } else if (purgeable === Purgeable.EVM_TRANSACTIONS) {
      await purgeTransactions();
    }
  };

  const { awaitTask } = useTaskStore();
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const refreshGeneralCache = async () => {
    const taskType = TaskType.REFRESH_GENERAL_CACHE;
    const { taskId } = await refreshGeneralCacheTask();
    try {
      await awaitTask<boolean, TaskMeta>(taskId, taskType, {
        title: t('actions.session.refresh_general_cache.task.title')
      });
    } catch (e: any) {
      if (!isTaskCancelled(e)) {
        notify({
          title: t('actions.session.refresh_general_cache.task.title'),
          message: t('actions.session.refresh_general_cache.error.message', {
            message: e.message
          }),
          display: true
        });
      }
    }
  };

  return {
    purgeCache,
    refreshGeneralCache
  };
};
