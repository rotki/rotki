import {
  ALL_CENTRALIZED_EXCHANGES,
  ALL_DECENTRALIZED_EXCHANGES,
  ALL_MODULES,
  ALL_TRANSACTIONS,
  type Purgeable
} from '@/types/session/purge';
import {
  SUPPORTED_EXCHANGES,
  type SupportedExchange,
  type SupportedExternalExchanges
} from '@/types/exchanges';
import { EXTERNAL_EXCHANGES } from '@/data/defaults';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { type TaskMeta, UserCancelledTaskError } from '@/types/task';

export const useSessionPurge = () => {
  const { resetState } = useDefiStore();
  const { reset } = useStaking();

  const { refreshGeneralCacheTask } = useSessionApi();

  const purgeExchange = async (
    exchange: SupportedExchange | typeof ALL_CENTRALIZED_EXCHANGES
  ): Promise<void> => {
    const { resetStatus } = useStatusUpdater(Section.TRADES);

    if (exchange === ALL_CENTRALIZED_EXCHANGES) {
      resetStatus();
      resetStatus(Section.ASSET_MOVEMENT);
    }
  };

  const purgeTransactions = async (): Promise<void> => {
    const { resetStatus } = useStatusUpdater(Section.HISTORY_EVENT);
    resetStatus();
  };

  const purgeCache = async (purgeable: Purgeable): Promise<void> => {
    if (purgeable === ALL_CENTRALIZED_EXCHANGES) {
      await purgeExchange(ALL_CENTRALIZED_EXCHANGES);
    } else if (purgeable === ALL_DECENTRALIZED_EXCHANGES) {
      resetState(ALL_DECENTRALIZED_EXCHANGES);
    } else if (purgeable === ALL_MODULES) {
      reset();
      resetState(ALL_MODULES);
    } else if (
      SUPPORTED_EXCHANGES.includes(purgeable as SupportedExchange) ||
      EXTERNAL_EXCHANGES.includes(purgeable as SupportedExternalExchanges)
    ) {
      await purgeExchange(purgeable as SupportedExchange);
    } else if (purgeable === ALL_TRANSACTIONS) {
      await purgeTransactions();
    } else if (Object.values(Module).includes(purgeable as Module)) {
      if ([Module.ETH2].includes(purgeable as Module)) {
        reset(purgeable as Module);
      } else {
        resetState(purgeable as Module);
      }
    }
  };

  const { awaitTask } = useTaskStore();
  const { t } = useI18n();

  const refreshGeneralCache = async () => {
    const taskType = TaskType.REFRESH_GENERAL_CACHE;
    const { taskId } = await refreshGeneralCacheTask();
    try {
      await awaitTask<boolean, TaskMeta>(taskId, taskType, {
        title: t('actions.session.refresh_general_cache.task.title')
      });
    } catch (e: any) {
      if (e instanceof UserCancelledTaskError) {
        logger.debug(e);
      }
    }
  };

  return {
    purgeCache,
    refreshGeneralCache
  };
};
