import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import type { KrakenStakingEvents, KrakenStakingPagination, ReceivedAmount } from '@/types/staking';
import type { TaskMeta } from '@/types/task';

function defaultPagination(): KrakenStakingPagination {
  return {
    offset: 0,
    limit: useFrontendSettingsStore().itemsPerPage,
    orderByAttributes: ['timestamp'],
    ascending: [false],
  };
}

function defaultEventState(): KrakenStakingEvents {
  return {
    assets: [],
    entriesTotal: 0,
    entriesFound: 0,
    entriesLimit: 0,
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

    const receivedAssets: Record<string, ReceivedAmount> = {};

    received.forEach((item: ReceivedAmount) => {
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

  const { isTaskRunning, awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { isFirstLoad, loading, setStatus, resetStatus } = useStatusUpdater(Section.STAKING_KRAKEN);

  const refreshEvents = async (): Promise<void> => {
    const { taskId } = await api.refreshKrakenStaking();

    const taskMeta: TaskMeta = {
      title: t('actions.kraken_staking.task.title').toString(),
    };

    await awaitTask<KrakenStakingEvents, TaskMeta>(taskId, TaskType.STAKING_KRAKEN, taskMeta, true);
  };

  const fetchEvents = async (refresh = false): Promise<void> => {
    const taskType = TaskType.STAKING_KRAKEN;
    try {
      const firstLoad = isFirstLoad();
      if (get(isTaskRunning(taskType)) || (loading() && refresh))
        return;

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      if (refresh || firstLoad) {
        if (firstLoad)
          set(rawEvents, await api.fetchKrakenStakingEvents(get(pagination)));

        setStatus(Status.REFRESHING);
        await refreshEvents();
      }
      set(rawEvents, await api.fetchKrakenStakingEvents(get(pagination)));

      setStatus(get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED);
    }
    catch (error: any) {
      logger.error(error);
      resetStatus();
      notify({
        title: t('actions.kraken_staking.error.title').toString(),
        message: t('actions.kraken_staking.error.message', {
          message: error.message,
        }).toString(),
        display: true,
      });
    }
  };

  const updatePagination = async (data: KrakenStakingPagination): Promise<void> => {
    set(pagination, data);
    await fetchEvents();
  };

  return {
    pagination,
    events,
    updatePagination,
    load: fetchEvents,
  };
});
