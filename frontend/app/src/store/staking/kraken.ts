import type {
  KrakenStakingDateFilter,
  KrakenStakingEvents,
  KrakenStakingPagination,
} from '@/types/staking';
import type { TaskMeta } from '@/types/task';
import { useKrakenApi } from '@/composables/api/staking/kraken';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useStatusUpdater } from '@/composables/status';
import { useNotificationsStore } from '@/store/notifications';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useTaskStore } from '@/store/tasks';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { balanceSum } from '@/utils/calculation';
import { logger } from '@/utils/logging';
import { type AssetBalance, Zero } from '@rotki/common';
import { omit } from 'es-toolkit';

function defaultPagination(): KrakenStakingPagination {
  return {
    ascending: [false],
    limit: useFrontendSettingsStore().itemsPerPage,
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
    totalUsdValue: Zero,
  };
}

export const useKrakenStakingStore = defineStore('staking/kraken', () => {
  const pagination = ref<KrakenStakingPagination>(defaultPagination());
  const rawEvents = ref<KrakenStakingEvents>(defaultEventState());

  const api = useKrakenApi();

  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();
  const { t } = useI18n();

  const events = computed<KrakenStakingEvents>(() => {
    const eventsValue = get(rawEvents);
    const received = eventsValue.received;

    const receivedAssets: Record<string, AssetBalance> = {};

    received.forEach((item: AssetBalance) => {
      const associatedAsset: string = get(getAssociatedAssetIdentifier(item.asset));

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
  const { notify } = useNotificationsStore();
  const { isFirstLoad, loading, resetStatus, setStatus } = useStatusUpdater(Section.STAKING_KRAKEN);

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
      if (get(isTaskRunning(taskType)) || (loading() && refresh))
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

      setStatus(get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED);
    }
    catch (error: any) {
      logger.error(error);
      resetStatus();
      notify({
        display: true,
        message: t('actions.kraken_staking.error.message', {
          message: error.message,
        }),
        title: t('actions.kraken_staking.error.title'),
      });
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
