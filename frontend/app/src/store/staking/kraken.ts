import { useStatusUpdater } from '@/composables/status';
import { useKrakenApi } from '@/services/staking/kraken';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { useNotifications } from '@/store/notifications';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useTasks } from '@/store/tasks';
import {
  KrakenStakingEvents,
  KrakenStakingPagination,
  ReceivedAmount
} from '@/types/staking';
import { Section, Status } from '@/types/status';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { Zero } from '@/utils/bignumbers';
import { balanceSum } from '@/utils/calculation';
import { logger } from '@/utils/logging';

const defaultPagination = (): KrakenStakingPagination => ({
  offset: 0,
  limit: useFrontendSettingsStore().itemsPerPage,
  orderByAttributes: ['timestamp'],
  ascending: [false]
});

const defaultEventState = (): KrakenStakingEvents => ({
  assets: [],
  entriesTotal: 0,
  entriesFound: 0,
  entriesLimit: 0,
  events: [],
  received: [],
  totalUsdValue: Zero
});

export const useKrakenStakingStore = defineStore('staking/kraken', () => {
  const pagination = ref(defaultPagination());
  const rawEvents = ref<KrakenStakingEvents>(defaultEventState());

  const api = useKrakenApi();

  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();
  const { t } = useI18n();

  const events = computed<KrakenStakingEvents>(() => {
    const eventsValue = get(rawEvents) as KrakenStakingEvents;
    const received = eventsValue.received;

    const receivedAssets: Record<string, ReceivedAmount> = {};

    received.forEach((item: ReceivedAmount) => {
      const associatedAsset: string = get(
        getAssociatedAssetIdentifier(item.asset)
      );

      const receivedAsset = receivedAssets[associatedAsset];

      receivedAssets[associatedAsset] = !receivedAsset
        ? {
            ...item
          }
        : {
            ...item,
            ...balanceSum(receivedAsset, item)
          };
    });

    return {
      ...eventsValue,
      assets: Object.keys(receivedAssets),
      received: Object.values(receivedAssets)
    };
  });

  const { isTaskRunning, awaitTask } = useTasks();
  const { notify } = useNotifications();
  const { isFirstLoad, loading, setStatus, resetStatus } = useStatusUpdater(
    Section.STAKING_KRAKEN
  );

  const refreshEvents = async () => {
    const { taskId } = await api.refreshKrakenStaking();

    const taskMeta: TaskMeta = {
      title: t('actions.kraken_staking.task.title').toString(),
      numericKeys: []
    };

    await awaitTask<KrakenStakingEvents, TaskMeta>(
      taskId,
      TaskType.STAKING_KRAKEN,
      taskMeta,
      true
    );
  };

  const fetchEvents = async (refresh: boolean = false) => {
    const taskType = TaskType.STAKING_KRAKEN;
    try {
      const firstLoad = isFirstLoad();
      if (get(isTaskRunning(taskType)) || (loading() && refresh)) {
        return;
      }

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      if (refresh || firstLoad) {
        if (firstLoad) {
          set(rawEvents, await api.fetchKrakenStakingEvents(get(pagination)));
        }
        setStatus(Status.REFRESHING);
        await refreshEvents();
      }
      set(rawEvents, await api.fetchKrakenStakingEvents(get(pagination)));

      setStatus(
        get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
      );
    } catch (e: any) {
      logger.error(e);
      resetStatus();
      notify({
        title: t('actions.kraken_staking.error.title').toString(),
        message: t('actions.kraken_staking.error.message', {
          message: e.message
        }).toString(),
        display: true
      });
    }
  };

  const updatePagination = async (data: KrakenStakingPagination) => {
    set(pagination, data);
    await fetchEvents();
  };

  return {
    pagination,
    events,
    updatePagination,
    load: fetchEvents
  };
});
