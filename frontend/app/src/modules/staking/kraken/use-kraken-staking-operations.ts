import type { KrakenStakingPagination } from '@/modules/staking/staking-types';
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
  fetchEvents: (refresh?: boolean) => Promise<void>;
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

  /**
   * Only a refresh has to stand down for one already running: a second would stack on the same
   * backend task. A plain read is a cached call that always sends the pagination as it stands, so
   * it can run alongside — which is what lets a filter changed mid-refresh reach the table instead
   * of being dropped.
   */
  function shouldSkip(refresh: boolean): boolean {
    return refresh && (isRefreshRunning() || get(loading));
  }

  async function fetchEventsFromApi(): Promise<void> {
    set(rawEvents, await api.fetchKrakenStakingEvents(get(pagination)));
  }

  /**
   * Loads the events, refreshing the backend cache first where that is due.
   *
   * @remarks
   * Every call cancels the reads before it, so `loading` belongs to the newest one alone. A read
   * that finds itself cancelled therefore leaves the flag as it is: clearing it would hide the
   * spinner while the read that superseded it is still running.
   *
   * @param refresh - whether the user asked for this, rather than it being the page's first load
   */
  async function fetchEvents(refresh = false): Promise<void> {
    try {
      if (shouldSkip(refresh))
        return;

      api.cancelPendingEventReads();

      const firstLoad = !get(loadedOnce);
      set(loading, true);

      // On first load, show cached data immediately while the backend refreshes
      if (firstLoad)
        await fetchEventsFromApi();

      if ((refresh || firstLoad) && !isRefreshRunning()) {
        const outcome = await refreshEvents();
        onActionableError(outcome, (error) => {
          logger.error(error.message);
          notifyError(
            t('actions.kraken_staking.error.title'),
            t('actions.kraken_staking.error.message', { message: error.message }),
          );
        });
      }

      await fetchEventsFromApi();
      set(loadedOnce, true);
      set(loading, isRefreshRunning());
    }
    catch (error: unknown) {
      if (isRequestCancellation(error))
        return;

      set(loading, false);

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
