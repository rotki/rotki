import { ref } from '@vue/composition-api';
import { defineStore } from 'pinia';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { Section, Status } from '@/store/const';
import { useNotifications } from '@/store/notifications';
import store from '@/store/store';
import { useTasks } from '@/store/tasks';
import { getStatusUpdater } from '@/store/utils';
import { KrakenStakingEvents, KrakenStakingPagination } from '@/types/staking';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { Zero } from '@/utils/bignumbers';
import { logger } from '@/utils/logging';

const defaultPagination = (): KrakenStakingPagination => ({
  offset: 0,
  limit: store.state.settings!.itemsPerPage,
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
  const events = ref<KrakenStakingEvents>(defaultEventState());

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
      if (isTaskRunning(taskType).value || (loading() && refresh)) {
        return;
      }

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      if (refresh || firstLoad) {
        if (firstLoad) {
          events.value = await api.fetchKrakenStakingEvents(pagination.value);
        }
        setStatus(Status.REFRESHING);
        await refreshEvents();
      }
      events.value = await api.fetchKrakenStakingEvents(pagination.value);

      setStatus(
        isTaskRunning(taskType).value ? Status.REFRESHING : Status.LOADED
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
    pagination.value = data;
    await fetchEvents();
  };

  return {
    pagination,
    events,
    updatePagination,
    load: fetchEvents
  };
});
