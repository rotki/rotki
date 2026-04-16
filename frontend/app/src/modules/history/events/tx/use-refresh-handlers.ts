import type { TaskMeta } from '@/modules/core/tasks/types';
import { groupBy, omit } from 'es-toolkit';
import { type Exchange, QueryExchangeEventsPayload } from '@/modules/balances/types/exchanges';
import { awaitParallelExecution } from '@/modules/core/common/async/await-parallel-execution';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import { useEventsQueryStatusStore } from '@/modules/history/use-events-query-status-store';
import { useMoneriumOAuth } from '@/modules/integrations/monerium/use-monerium-auth';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { Module, useModuleEnabled } from '@/modules/session/use-module-enabled';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';

interface UseRefreshHandlersReturn {
  queryAllExchangeEvents: (exchanges: Exchange[]) => Promise<void>;
  queryOnlineEvent: (queryType: OnlineHistoryEventsQueryType) => Promise<void>;
}

export function useRefreshHandlers(): UseRefreshHandlersReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();
  const { markLocationCancelled } = useEventsQueryStatusStore();
  const { queryExchangeEvents, queryOnlineHistoryEvents } = useHistoryEventsApi();
  const { runTask } = useTaskHandler();
  const { enabled: isEth2Enabled } = useModuleEnabled(Module.ETH2);
  const { getApiKey } = useExternalApiKeys();
  const { authenticated: moneriumAuthenticated, refreshStatus } = useMoneriumOAuth();
  const { allowed: gnosisPayAllowed } = useFeatureAccess(PremiumFeature.GNOSIS_PAY);
  const { allowed: moneriumAllowed } = useFeatureAccess(PremiumFeature.MONERIUM);

  const queryOnlineEvent = async (queryType: OnlineHistoryEventsQueryType): Promise<void> => {
    const eth2QueryTypes: OnlineHistoryEventsQueryType[] = [
      OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
      OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS,
    ];

    if (!get(isEth2Enabled) && eth2QueryTypes.includes(queryType))
      return;

    if (queryType === OnlineHistoryEventsQueryType.GNOSIS_PAY && (!get(gnosisPayAllowed) || !getApiKey('gnosis_pay'))) {
      return;
    }

    if (queryType === OnlineHistoryEventsQueryType.MONERIUM) {
      if (!get(moneriumAllowed))
        return;

      await refreshStatus();
      if (!get(moneriumAuthenticated)) {
        return;
      }
    }

    logger.debug(`querying for ${queryType} events`);

    const taskMeta = {
      description: t('actions.online_events.task.description', { queryType }),
      queryType,
      title: t('actions.online_events.task.title'),
    };

    const outcome = await runTask<boolean, TaskMeta>(
      async () => queryOnlineHistoryEvents({ asyncQuery: true, queryType }),
      { type: TaskType.QUERY_ONLINE_EVENTS, meta: taskMeta, unique: false },
    );

    if (isActionableFailure(outcome)) {
      logger.error(outcome.error);
      notifyError(
        t('actions.online_events.error.title'),
        t('actions.online_events.error.description', {
          error: outcome.message,
          queryType,
        }),
      );
    }
    logger.debug(`finished querying for ${queryType} events`);
  };

  const queryExchange = async (payload: Exchange): Promise<void> => {
    logger.debug(`querying exchange events for ${payload.location} (${payload.name})`);
    const exchange = omit(payload, ['krakenAccountType', 'okxLocation']);
    const taskMeta = {
      description: t('actions.exchange_events.task.description', exchange),
      exchange,
      title: t('actions.exchange_events.task.title'),
    };

    const parsedPayload = QueryExchangeEventsPayload.parse(exchange);
    const outcome = await runTask<boolean, TaskMeta>(
      async () => queryExchangeEvents(parsedPayload),
      { type: TaskType.QUERY_EXCHANGE_EVENTS, meta: taskMeta, unique: false },
    );

    if (!outcome.success) {
      if (outcome.cancelled) {
        markLocationCancelled({ location: exchange.location, name: exchange.name });
      }
      else if (!outcome.skipped) {
        logger.error(outcome.error);
        notifyError(
          t('actions.exchange_events.error.title'),
          t('actions.exchange_events.error.description', {
            error: outcome.message,
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
