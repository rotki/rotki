import { computed, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { defineStore } from 'pinia';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { useAssetInfoRetrieval } from '@/store/assets';
import { Section, Status } from '@/store/const';
import { useNotifications } from '@/store/notifications';
import { useFrontendSettingsStore } from '@/store/settings';
import { useTasks } from '@/store/tasks';
import { getStatusUpdater } from '@/store/utils';
import {
  KrakenStakingEvents,
  KrakenStakingPagination,
  ReceivedAmount
} from '@/types/staking';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { Zero } from '@/utils/bignumbers';
import { balanceSum } from '@/utils/calculation';
import { logger } from '@/utils/logging';

const defaultPagination = (): KrakenStakingPagination => ({
  offset: 0,
  limit: useFrontendSettingsStore().itemsPerPage,
  orderByAttribute: 'timestamp',
  ascending: false
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

  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();

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
  const { isFirstLoad, loading, setStatus, resetStatus } = getStatusUpdater(
    Section.STAKING_KRAKEN
  );

  const refreshEvents = async () => {
    const { taskId } = await api.refreshKrakenStaking();

    const taskMeta: TaskMeta = {
      title: i18n.t('actions.kraken_staking.task.title').toString(),
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
        title: i18n.t('actions.kraken_staking.error.title').toString(),
        message: i18n
          .t('actions.kraken_staking.error.message', { message: e.message })
          .toString(),
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
