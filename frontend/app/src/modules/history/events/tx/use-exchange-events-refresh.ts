import { toSentenceCase } from '@rotki/common';
import { omit } from 'es-toolkit';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { type Exchange, QueryExchangeEventsPayload } from '@/modules/balances/types/exchanges';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, isCancellation, type TaskError } from '@/modules/core/tasks/task-result';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { exchangeEventsActivityId } from '@/modules/history/events/tx/sync-activity';
import { useEventsQueryStatusStore } from '@/modules/history/use-events-query-status-store';
import { EXCHANGE_EVENTS_LANE_PREFIX, familyLane } from '@/modules/task-center/core/orchestrator/spec';
import { type ActivityId, ActivityKind } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseExchangeEventsRefreshReturn {
  queryAllExchangeEvents: (exchanges: Exchange[], parent?: ActivityId) => Promise<void>;
}

/**
 * Queries exchange history events. Each {location, name} account runs as its own native
 * EXCHANGE_EVENTS activity, so the orchestrator owns liveness (read off
 * `useWorkStatus(ActivityKind.EXCHANGE_EVENTS)`), cancellation and re-run. The cap-2,
 * sequential-within-location fan-out lives in {@link queryAllExchangeEvents}.
 */
export function useExchangeEventsRefresh(): UseExchangeEventsRefreshReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();
  const { markLocationCancelled } = useEventsQueryStatusStore();
  const { queryExchangeEvents } = useHistoryEventsApi();
  const { submitTask } = useNativeTask();

  const queryExchange = async (payload: Exchange, parent?: ActivityId): Promise<void> => {
    logger.debug(`querying exchange events for ${payload.location} (${payload.name})`);
    const exchange = omit(payload, ['gateLocation', 'krakenAccountType', 'okxLocation']);
    const parsedPayload = QueryExchangeEventsPayload.parse(exchange);
    const outcome = await submitTask({
      id: exchangeEventsActivityId(exchange.location, exchange.name),
      kind: ActivityKind.EXCHANGE_EVENTS,
      // The location's own lane, capped at 1: one exchange's accounts query in sequence, and the
      // family's active cap decides how many locations run at once.
      lane: familyLane(EXCHANGE_EVENTS_LANE_PREFIX, exchange.location),
      parent,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => queryExchangeEvents(parsedPayload),
        ),
        () => {},
      ),
      subtitle: `${toSentenceCase(exchange.location)} · ${exchange.name}`,
      title: t('task_center.group.exchange_events'),
    });

    if (isErr(outcome)) {
      if (isCancellation(outcome.error)) {
        markLocationCancelled({ location: exchange.location, name: exchange.name });
      }
      else if (isActionable(outcome.error)) {
        logger.error(outcome.error);
        notifyError(
          t('actions.exchange_events.error.title'),
          t('actions.exchange_events.error.description', {
            error: outcome.error.message,
            ...payload,
          }),
        );
      }
    }
  };

  /**
   * Accounts of the same location run sequentially; distinct locations run two at a time.
   *
   * That shape is the lanes' now — a per-location lane capped at 1, with the family's active cap
   * allowing two locations. It used to be a hand-rolled `awaitGroupedExecution(..., 2)` wrapped
   * around work the scheduler was already governing, so the effective limit was the tighter of two
   * mechanisms and neither was written down.
   */
  const queryAllExchangeEvents = async (exchanges: Exchange[], parent?: ActivityId): Promise<void> => {
    await Promise.all(exchanges.map(async exchange => queryExchange(exchange, parent)));
  };

  return {
    queryAllExchangeEvents,
  };
}
