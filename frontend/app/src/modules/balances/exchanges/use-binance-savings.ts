import type { MaybeRef } from '@vueuse/core';
import type {
  ExchangeSavingsCollection,
  ExchangeSavingsCollectionResponse,
  ExchangeSavingsRequestPayload,
} from '@/types/exchanges';
import type { TaskMeta } from '@/types/task';
import { useExchangeApi } from '@/composables/api/balances/exchanges';
import { useStatusUpdater } from '@/composables/status';
import { useNotificationsStore } from '@/store/notifications';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useTaskStore } from '@/store/tasks';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { mapCollectionResponse } from '@/utils/collection';
import { uniqueStrings } from '@/utils/data';
import { logger } from '@/utils/logging';

interface UseBinanceSavingsReturn {
  fetchExchangeSavings: (payload: MaybeRef<ExchangeSavingsRequestPayload>) => Promise<ExchangeSavingsCollection>;
  refreshExchangeSavings: (userInitiated?: boolean) => Promise<void>;
}

export function useBinanceSavings(): UseBinanceSavingsReturn {
  const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
  const { awaitTask, isTaskRunning } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { getExchangeSavings, getExchangeSavingsTask } = useExchangeApi();
  const { t } = useI18n({ useScope: 'global' });

  const fetchExchangeSavings = async (
    payload: MaybeRef<ExchangeSavingsRequestPayload>,
  ): Promise<ExchangeSavingsCollection> => {
    const response = await getExchangeSavings({
      ...get(payload),
      onlyCache: true,
    });

    return mapCollectionResponse(response);
  };

  const syncExchangeSavings = async (location: string): Promise<boolean> => {
    const taskType = TaskType.QUERY_EXCHANGE_SAVINGS;

    const defaults: ExchangeSavingsRequestPayload = {
      ascending: [false],
      limit: 0,
      location,
      offset: 0,
      orderByAttributes: ['timestamp'],
    };

    const { taskId } = await getExchangeSavingsTask(defaults);

    const taskMeta = {
      title: t('actions.balances.exchange_savings_interest.task.title', {
        location,
      }),
    };

    try {
      await awaitTask<ExchangeSavingsCollectionResponse, TaskMeta>(taskId, taskType, taskMeta, true);
      return true;
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        notify({
          display: true,
          message: t('actions.balances.exchange_savings_interest.error.message', { location }),
          title: t('actions.balances.exchange_savings_interest.error.title', {
            location,
          }),
        });
      }
    }

    return false;
  };

  const refreshExchangeSavings = async (userInitiated = false): Promise<void> => {
    const { fetchDisabled, resetStatus, setStatus } = useStatusUpdater(Section.EXCHANGE_SAVINGS);

    if (fetchDisabled(userInitiated)) {
      logger.info('skipping exchanges savings');
      return;
    }

    setStatus(Status.REFRESHING);

    try {
      const locations = get(connectedExchanges)
        .map(({ location }) => location)
        .filter(uniqueStrings)
        .filter(location => ['binance', 'binanceus'].includes(location));

      if (locations.length > 0)
        await Promise.all(locations.map(syncExchangeSavings));

      setStatus(isTaskRunning(TaskType.QUERY_EXCHANGE_SAVINGS) ? Status.REFRESHING : Status.LOADED);
    }
    catch (error) {
      logger.error(error);
      resetStatus();
    }
  };

  return {
    fetchExchangeSavings,
    refreshExchangeSavings,
  };
}
