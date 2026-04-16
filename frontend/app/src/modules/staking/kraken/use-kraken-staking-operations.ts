import type {
  KrakenStakingDateFilter,
  KrakenStakingPagination,
} from '@/modules/staking/staking-types';
import type { TaskMeta } from '@/modules/tasks/types';
import { omit } from 'es-toolkit';
import { useKrakenApi } from '@/composables/api/staking/kraken';
import { useStatusUpdater } from '@/composables/status';
import { logger } from '@/modules/common/logging/logging';
import { Section, Status } from '@/modules/common/status';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';
import { TaskType } from '@/modules/tasks/task-type';
import { useTaskHandler } from '@/modules/tasks/use-task-handler';
import { useTaskStore } from '@/modules/tasks/use-task-store';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useKrakenStakingStore } from '@/store/staking/kraken';

interface UseKrakenStakingOperationsReturn {
  fetchEvents: (refresh?: boolean, dateFilter?: KrakenStakingDateFilter) => Promise<void>;
  updatePagination: (data: KrakenStakingPagination) => Promise<void>;
}

export function useKrakenStakingOperations(): UseKrakenStakingOperationsReturn {
  const api = useKrakenApi();
  const { runTask } = useTaskHandler();
  const { isTaskRunning } = useTaskStore();
  const { notifyError } = useNotifications();
  const { isFirstLoad, loading, setStatus } = useStatusUpdater(Section.STAKING_KRAKEN);
  const { t } = useI18n({ useScope: 'global' });
  const { pagination, rawEvents } = storeToRefs(useKrakenStakingStore());
  const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());

  watchImmediate(itemsPerPage, (newValue: number) => {
    set(pagination, { ...get(pagination), limit: newValue });
  });

  async function refreshEvents(): Promise<void> {
    await runTask<unknown, TaskMeta>(
      async () => api.refreshKrakenStaking(),
      { type: TaskType.STAKING_KRAKEN, meta: { title: t('actions.kraken_staking.task.title') }, unique: false },
    );
  }

  function buildQuery(dateFilter?: KrakenStakingDateFilter): KrakenStakingPagination {
    return {
      ...omit(get(pagination), ['fromTimestamp', 'toTimestamp']),
      ...dateFilter,
    };
  }

  function shouldSkip(refresh: boolean): boolean {
    return isTaskRunning(TaskType.STAKING_KRAKEN) || (loading() && refresh);
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

      const firstLoad = isFirstLoad();
      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      // On first load, show cached data immediately while the backend refreshes
      if (firstLoad)
        await fetchEventsFromApi(dateFilter);

      if (refresh || firstLoad) {
        setStatus(Status.REFRESHING);
        await refreshEvents();
      }

      // Fetch the (possibly updated) events from the backend
      await fetchEventsFromApi(dateFilter);
      setStatus(isTaskRunning(TaskType.STAKING_KRAKEN) ? Status.REFRESHING : Status.LOADED);
    }
    catch (error: unknown) {
      logger.error(error);
      setStatus(Status.LOADED);
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
