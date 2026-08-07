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

  async function fetchEvents(refresh = false): Promise<void> {
    try {
      if (shouldSkip(refresh))
        return;

      // A read still in flight was started for an older filter. Left alone it can land after this
      // one and overwrite it, leaving the table showing rows the pills no longer describe, so it
      // is cancelled rather than raced.
      api.cancelPendingEventReads();

      const firstLoad = !get(loadedOnce);
      set(loading, true);

      // On first load, show cached data immediately while the backend refreshes
      if (firstLoad)
        await fetchEventsFromApi();

      // A running refresh is already doing this work, so the first load rides it out and takes the
      // read below rather than stacking a second one on the same task.
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

      // Fetch the (possibly updated) events from the backend. It reads the pagination as it stands
      // now, not as it stood when this call started, so a filter changed while the refresh ran is
      // the one that gets queried.
      await fetchEventsFromApi();
      set(loadedOnce, true);
      set(loading, isRefreshRunning());
    }
    catch (error: unknown) {
      // A cancelled read was superseded by a newer one, which owns `loading` from here on:
      // clearing it would hide the spinner while that newer read is still running.
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
