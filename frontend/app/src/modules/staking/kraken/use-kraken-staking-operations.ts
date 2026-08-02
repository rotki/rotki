import type {
  KrakenStakingDateFilter,
  KrakenStakingPagination,
} from '@/modules/staking/staking-types';
import { omit } from 'es-toolkit';
import { map as mapResult, type Result } from 'plainfp/result';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { useSetting } from '@/modules/settings/use-setting';
import { useKrakenApi } from '@/modules/staking/api/use-kraken-api';
import { useKrakenStakingStore } from '@/modules/staking/use-kraken-staking-store';
import { activityLabel } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { type TaskOutcome, useNativeTask } from '@/modules/task-center/use-native-task';

interface UseKrakenStakingOperationsReturn {
  fetchEvents: (refresh?: boolean, dateFilter?: KrakenStakingDateFilter) => Promise<void>;
  updatePagination: (data: KrakenStakingPagination) => Promise<void>;
}

export function useKrakenStakingOperations(): UseKrakenStakingOperationsReturn {
  const api = useKrakenApi();
  const { statusOf, submitTask } = useNativeTask();
  const { notifyError } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });
  const { loadedOnce, loading, pagination, rawEvents } = storeToRefs(useKrakenStakingStore());
  const itemsPerPage = useSetting('itemsPerPage');

  watchImmediate(itemsPerPage, (newValue: number) => {
    set(pagination, { ...get(pagination), limit: newValue });
  });

  function isRefreshRunning(): boolean {
    return statusOf(ActivityKind.STAKING, ActivityPart.KRAKEN).running;
  }

  async function refreshEvents(): Promise<TaskOutcome> {
    return submitTask({
      id: makeActivityId(ActivityKind.STAKING, ActivityPart.KRAKEN),
      kind: ActivityKind.STAKING,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<unknown>(
          async () => api.refreshKrakenStaking(),
        ),
        () => {},
      ),
      subtitle: activityLabel(ActivityKind.STAKING, ActivityPart.KRAKEN),
      title: t('task_center.group.staking'),
    });
  }

  function buildQuery(dateFilter?: KrakenStakingDateFilter): KrakenStakingPagination {
    return {
      ...omit(get(pagination), ['fromTimestamp', 'toTimestamp']),
      ...dateFilter,
    };
  }

  function shouldSkip(refresh: boolean): boolean {
    return isRefreshRunning() || (get(loading) && refresh);
  }

  async function fetchEventsFromApi(dateFilter?: KrakenStakingDateFilter): Promise<void> {
    set(rawEvents, await api.fetchKrakenStakingEvents(buildQuery(dateFilter)));
  }

  async function fetchEvents(
    refresh = false,
    dateFilter?: KrakenStakingDateFilter,
  ): Promise<void> {
    try {
      if (shouldSkip(refresh))
        return;

      const firstLoad = !get(loadedOnce);
      set(loading, true);

      // On first load, show cached data immediately while the backend refreshes
      if (firstLoad)
        await fetchEventsFromApi(dateFilter);

      if (refresh || firstLoad) {
        const outcome = await refreshEvents();
        onActionableError(outcome, (error) => {
          logger.error(error.message);
          notifyError(
            t('actions.kraken_staking.error.title'),
            t('actions.kraken_staking.error.message', { message: error.message }),
          );
        });
      }

      // Fetch the (possibly updated) events from the backend
      await fetchEventsFromApi(dateFilter);
      set(loadedOnce, true);
      set(loading, isRefreshRunning());
    }
    catch (error: unknown) {
      set(loading, false);

      if (isRequestCancellation(error))
        return;

      logger.error(error);
      notifyError(
        t('actions.kraken_staking.error.title'),
        t('actions.kraken_staking.error.message', {
          message: getErrorMessage(error),
        }),
      );
    }
  }

  async function updatePagination(data: KrakenStakingPagination): Promise<void> {
    set(pagination, data);
    await fetchEvents();
  }

  return {
    fetchEvents,
    updatePagination,
  };
}
