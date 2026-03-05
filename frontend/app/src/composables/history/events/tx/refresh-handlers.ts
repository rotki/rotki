import type { TaskMeta } from '@/types/task';
import { groupBy, omit } from 'es-toolkit';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useModules } from '@/composables/session/modules';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';
import { useMoneriumOAuth } from '@/modules/external-services/monerium/use-monerium-auth';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { useEventsQueryStatusStore } from '@/store/history/query-status/events-query-status';
import { useTaskStore } from '@/store/tasks';
import { type Exchange, QueryExchangeEventsPayload } from '@/types/exchanges';
import { OnlineHistoryEventsQueryType } from '@/types/history/events/schemas';
import { Module } from '@/types/modules';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { logger } from '@/utils/logging';

interface UseRefreshHandlersReturn {
  queryAllExchangeEvents: (exchanges: Exchange[]) => Promise<void>;
  queryOnlineEvent: (queryType: OnlineHistoryEventsQueryType) => Promise<void>;
}

export function useRefreshHandlers(): UseRefreshHandlersReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();
  const { markLocationCancelled } = useEventsQueryStatusStore();
  const { queryExchangeEvents, queryOnlineHistoryEvents } = useHistoryEventsApi();
  const { awaitTask } = useTaskStore();
  const { isModuleEnabled } = useModules();
  const isEth2Enabled = isModuleEnabled(Module.ETH2);
  const { apiKey } = useExternalApiKeys(t);
  const { authenticated: moneriumAuthenticated, refreshStatus } = useMoneriumOAuth();

  const queryOnlineEvent = async (queryType: OnlineHistoryEventsQueryType): Promise<void> => {
    const eth2QueryTypes: OnlineHistoryEventsQueryType[] = [
      OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
      OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS,
    ];

    if (!get(isEth2Enabled) && eth2QueryTypes.includes(queryType))
      return;

    if (!get(apiKey('gnosis_pay')) && queryType === OnlineHistoryEventsQueryType.GNOSIS_PAY) {
      return;
    }

    if (queryType === OnlineHistoryEventsQueryType.MONERIUM) {
      await refreshStatus();
      if (!get(moneriumAuthenticated)) {
        return;
      }
    }

    logger.debug(`querying for ${queryType} events`);
    const taskType = TaskType.QUERY_ONLINE_EVENTS;
    const { taskId } = await queryOnlineHistoryEvents({
      asyncQuery: true,
      queryType,
    });

    const taskMeta = {
      description: t('actions.online_events.task.description', {
        queryType,
      }),
      queryType,
      title: t('actions.online_events.task.title'),
    };

    try {
      await awaitTask<boolean, TaskMeta>(taskId, taskType, taskMeta, true);
    }
    catch (error: unknown) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        notifyError(
          t('actions.online_events.error.title'),
          t('actions.online_events.error.description', {
            error,
            queryType,
          }),
        );
      }
    }
    logger.debug(`finished querying for ${queryType} events`);
  };

  const queryExchange = async (payload: Exchange): Promise<void> => {
    logger.debug(`querying exchange events for ${payload.location} (${payload.name})`);
    const exchange = omit(payload, ['krakenAccountType', 'okxLocation']);
    const taskType = TaskType.QUERY_EXCHANGE_EVENTS;
    const taskMeta = {
      description: t('actions.exchange_events.task.description', exchange),
      exchange,
      title: t('actions.exchange_events.task.title'),
    };

    try {
      const payload = QueryExchangeEventsPayload.parse(exchange);
      const { taskId } = await queryExchangeEvents(payload);
      await awaitTask<boolean, TaskMeta>(taskId, taskType, taskMeta, true);
    }
    catch (error: unknown) {
      if (isTaskCancelled(error)) {
        markLocationCancelled({ location: exchange.location, name: exchange.name });
      }
      else {
        logger.error(error);
        notifyError(
          t('actions.exchange_events.error.title'),
          t('actions.exchange_events.error.description', {
            error,
            ...payload,
          }),
        );
      }
    }
  };

  const queryAllExchangeEvents = async (exchanges: Exchange[]): Promise<void> => {
    const groupedExchanges = Object.entries(groupBy(exchanges, exchange => exchange.location));

    await awaitParallelExecution(groupedExchanges, ([group]) => group, async ([_group, exchanges]) => {
      for (const exchange of exchanges) {
        await queryExchange(exchange);
      }
    }, 2);
  };

  return {
    queryAllExchangeEvents,
    queryOnlineEvent,
  };
}
