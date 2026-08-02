import type { MaybeRef } from 'vue';
import type {
  ExchangeSavingsCollection,
  ExchangeSavingsCollectionResponse,
  ExchangeSavingsRequestPayload,
} from '@/modules/balances/types/exchanges';
import { toSentenceCase } from '@rotki/common';
import { pipe } from 'plainfp';
import { filter, unique } from 'plainfp/arrays';
import { map as mapResult, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useExchangeApi } from '@/modules/balances/api/use-exchange-api';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { mapCollectionResponse } from '@/modules/core/common/data/collection-utils';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { EXCHANGE_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { ActivityKind, makeActivityId, type WorkStatus } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseBinanceSavingsReturn {
  fetchExchangeSavings: (payload: MaybeRef<ExchangeSavingsRequestPayload>) => Promise<ExchangeSavingsCollection>;
  refreshExchangeSavings: (userInitiated?: boolean) => Promise<void>;
}

/** Only binance exposes a savings/interest history. */
const SAVINGS_LOCATIONS: ReadonlySet<string> = new Set(['binance', 'binanceus']);

/**
 * Whether a refresh should actually run — the functional restatement of the old `fetchDisabled`:
 * never while a sync is in flight, and automatically (non user-initiated) only before the first
 * successful load.
 */
function shouldRefresh(status: WorkStatus, userInitiated: boolean): boolean {
  return !status.active && (userInitiated || !status.everCompleted);
}

export function useBinanceSavings(): UseBinanceSavingsReturn {
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
  const { submitTask } = useNativeTask();
  const { useWorkStatus } = useTaskCenter();
  const { notifyError } = useNotifications();
  const { getExchangeSavings, getExchangeSavingsTask } = useExchangeApi();
  const { t } = useI18n({ useScope: 'global' });

  const savingsStatus = useWorkStatus(ActivityKind.EXCHANGE_SAVINGS);

  const fetchExchangeSavings = async (
    payload: MaybeRef<ExchangeSavingsRequestPayload>,
  ): Promise<ExchangeSavingsCollection> => {
    const response = await getExchangeSavings({
      ...get(payload),
      onlyCache: true,
    });

    return mapCollectionResponse(response);
  };

  // One native activity per binance location; the orchestrator owns liveness/freshness, read off
  // `useWorkStatus(ActivityKind.EXCHANGE_SAVINGS)`. The savings sync only triggers the backend
  // refresh — the cached events are re-read by the detail view once the activity settles.
  const syncExchangeSavings = async (location: string): Promise<void> => {
    const defaults: ExchangeSavingsRequestPayload = {
      ascending: [false],
      limit: 0,
      location,
      offset: 0,
      orderByAttributes: ['timestamp'],
    };

    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.EXCHANGE_SAVINGS, location),
      kind: ActivityKind.EXCHANGE_SAVINGS,
      lane: EXCHANGE_LANE,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<ExchangeSavingsCollectionResponse>(
          async () => getExchangeSavingsTask(defaults),
        ),
        () => {},
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.exchange_savings.interest'), { location: toSentenceCase(location) }),
      title: t('task_center.group.exchange_savings'),
    });

    onActionableError(outcome, () => {
      notifyError(
        t('actions.balances.exchange_savings_interest.error.title', { location }),
        t('actions.balances.exchange_savings_interest.error.message', { location }),
      );
    });
  };

  const savingsLocations = (): string[] => pipe(
    get(connectedExchanges).map(({ location }) => location),
    unique,
    filter(location => SAVINGS_LOCATIONS.has(location)),
  );

  const refreshExchangeSavings = async (userInitiated = false): Promise<void> => {
    if (!shouldRefresh(get(savingsStatus), userInitiated)) {
      logger.info('skipping exchanges savings');
      return;
    }

    await Promise.all(savingsLocations().map(syncExchangeSavings));
  };

  return {
    fetchExchangeSavings,
    refreshExchangeSavings,
  };
}
