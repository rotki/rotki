import type { MaybeRef } from 'vue';
import type {
  ExchangeSavingsCollection,
  ExchangeSavingsCollectionResponse,
  ExchangeSavingsRequestPayload,
} from '@/modules/balances/types/exchanges';
import type { TaskMeta } from '@/modules/tasks/types';
import { useExchangeApi } from '@/composables/api/balances/exchanges';
import { useStatusUpdater } from '@/composables/status';
import { Section, Status } from '@/modules/common/status';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';
import { useTaskStore } from '@/modules/tasks/use-task-store';
import { useSessionSettingsStore } from '@/store/settings/session';
import { mapCollectionResponse } from '@/utils/collection';
import { uniqueStrings } from '@/utils/data';
import { logger } from '@/utils/logging';

interface UseBinanceSavingsReturn {
  fetchExchangeSavings: (payload: MaybeRef<ExchangeSavingsRequestPayload>) => Promise<ExchangeSavingsCollection>;
  refreshExchangeSavings: (userInitiated?: boolean) => Promise<void>;
}

export function useBinanceSavings(): UseBinanceSavingsReturn {
  const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
  const { runTask } = useTaskHandler();
  const { isTaskRunning } = useTaskStore();
  const { notifyError } = useNotifications();
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
    const defaults: ExchangeSavingsRequestPayload = {
      ascending: [false],
      limit: 0,
      location,
      offset: 0,
      orderByAttributes: ['timestamp'],
    };

    const outcome = await runTask<ExchangeSavingsCollectionResponse, TaskMeta>(
      async () => getExchangeSavingsTask(defaults),
      {
        type: TaskType.QUERY_EXCHANGE_SAVINGS,
        meta: {
          title: t('actions.balances.exchange_savings_interest.task.title', {
            location,
          }),
        },
        unique: false,
      },
    );

    if (outcome.success)
      return true;

    if (isActionableFailure(outcome)) {
      notifyError(
        t('actions.balances.exchange_savings_interest.error.title', { location }),
        t('actions.balances.exchange_savings_interest.error.message', { location }),
      );
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
