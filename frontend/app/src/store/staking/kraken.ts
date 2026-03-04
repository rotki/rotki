import type {
  KrakenStakingDateFilter,
  KrakenStakingEvents,
  KrakenStakingPagination,
} from '@/types/staking';
import type { TaskMeta } from '@/types/task';
import { type AssetBalance, Zero } from '@rotki/common';
import { omit } from 'es-toolkit';
import { useKrakenApi } from '@/composables/api/staking/kraken';
import { useResolveAssetIdentifier } from '@/composables/assets/common';
import { useStatusUpdater } from '@/composables/status';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useTaskStore } from '@/store/tasks';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { balanceSum } from '@/utils/calculation';
import { logger } from '@/utils/logging';

function defaultPagination(itemsPerPage: number): KrakenStakingPagination {
  return {
    ascending: [false],
    limit: itemsPerPage,
    offset: 0,
    orderByAttributes: ['timestamp'],
  };
}

function defaultEventState(): KrakenStakingEvents {
  return {
    assets: [],
    entriesFound: 0,
    entriesLimit: 0,
    entriesTotal: 0,
    received: [],
    totalValue: Zero,
  };
}

export const useKrakenStakingStore = defineStore('staking/kraken', () => {
  const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());
  const pagination = ref<KrakenStakingPagination>(defaultPagination(get(itemsPerPage)));
  const rawEvents = ref<KrakenStakingEvents>(defaultEventState());

  watch(itemsPerPage, (newValue: number) => {
    set(pagination, { ...get(pagination), limit: newValue });
  });

  const api = useKrakenApi();

  const resolveAssetIdentifier = useResolveAssetIdentifier();
  const { t } = useI18n({ useScope: 'global' });

  const events = computed<KrakenStakingEvents>(() => {
    const eventsValue = get(rawEvents);
    const received = eventsValue.received;

    const receivedAssets: Record<string, AssetBalance> = {};

    received.forEach((item: AssetBalance) => {
      const associatedAsset: string = resolveAssetIdentifier(item.asset);

      const receivedAsset = receivedAssets[associatedAsset];

      receivedAssets[associatedAsset] = !receivedAsset
        ? {
            ...item,
          }
        : {
            ...item,
            ...balanceSum(receivedAsset, item),
          };
    });

    return {
      ...eventsValue,
      assets: Object.keys(receivedAssets),
      received: Object.values(receivedAssets),
    };
  });

  const { awaitTask, isTaskRunning } = useTaskStore();
  const { notifyError } = useNotifications();
  const { isFirstLoad, loading, setStatus } = useStatusUpdater(Section.STAKING_KRAKEN);

  const refreshEvents = async (): Promise<void> => {
    const { taskId } = await api.refreshKrakenStaking();

    const taskMeta: TaskMeta = {
      title: t('actions.kraken_staking.task.title'),
    };

    await awaitTask<KrakenStakingEvents, TaskMeta>(taskId, TaskType.STAKING_KRAKEN, taskMeta, true);
  };

  const fetchEvents = async (
    refresh = false,
    dateFilter?: KrakenStakingDateFilter,
  ): Promise<void> => {
    const taskType = TaskType.STAKING_KRAKEN;
    try {
      const firstLoad = isFirstLoad();
      if (isTaskRunning(taskType) || (loading() && refresh))
        return;

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      if (refresh || firstLoad) {
        if (firstLoad) {
          set(rawEvents, await api.fetchKrakenStakingEvents({
            ...omit(get(pagination), ['fromTimestamp', 'toTimestamp']),
            ...dateFilter,
          }));
        }

        setStatus(Status.REFRESHING);
        await refreshEvents();
      }
      set(rawEvents, await api.fetchKrakenStakingEvents({
        ...omit(get(pagination), ['fromTimestamp', 'toTimestamp']),
        ...dateFilter,
      }));

      setStatus(isTaskRunning(taskType) ? Status.REFRESHING : Status.LOADED);
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
  };

  const updatePagination = async (data: KrakenStakingPagination): Promise<void> => {
    set(pagination, data);
    await fetchEvents();
  };

  return {
    events,
    load: fetchEvents,
    pagination,
    updatePagination,
  };
});
