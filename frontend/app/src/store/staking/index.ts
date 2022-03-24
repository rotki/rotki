import {
  Eth2DailyStats,
  Eth2DailyStatsPayload,
  Eth2Deposits,
  Eth2Details
} from '@rotki/common/lib/staking/eth2';
import { ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { Module } from 'vuex';
import { getPremium } from '@/composables/session';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { Section, Status } from '@/store/const';
import { useNotifications } from '@/store/notifications';
import { StakingState } from '@/store/staking/types';
import store from '@/store/store';
import { useTasks } from '@/store/tasks';
import { RotkehlchenState } from '@/store/types';
import { getStatusUpdater } from '@/store/utils';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { Zero } from '@/utils/bignumbers';
import { logger } from '@/utils/logging';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state } from './state';

const defaultStats = () => ({
  entries: [],
  entriesFound: 0,
  entriesTotal: 0,
  sumPnl: Zero,
  sumUsdValue: Zero
});

const defaultPagination = (): Eth2DailyStatsPayload => {
  const itemsPerPage = store.state.settings!.itemsPerPage;

  return {
    limit: itemsPerPage,
    offset: 0,
    orderByAttribute: 'timestamp',
    ascending: false
  };
};

export const useEth2StakingStore = defineStore('staking/eth2', () => {
  const deposits = ref<Eth2Deposits>([]);
  const details = ref<Eth2Details>([]);
  const stats = ref<Eth2DailyStats>(defaultStats());
  const pagination = ref<Eth2DailyStatsPayload>(defaultPagination());
  const premium = getPremium();
  const { awaitTask, isTaskRunning } = useTasks();
  const { notify } = useNotifications();

  const fetchStakingDetails = async (refresh: boolean = false) => {
    if (!get(premium)) {
      return;
    }

    const { setStatus, loading, getStatus, resetStatus } = getStatusUpdater(
      Section.STAKING_ETH2
    );

    if (loading() || (getStatus() === Status.LOADED && !refresh)) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;

    async function fetchDetails() {
      setStatus(newStatus);
      try {
        const taskType = TaskType.STAKING_ETH2;
        const { taskId } = await api.eth2StakingDetails();
        const { result } = await awaitTask<Eth2Details, TaskMeta>(
          taskId,
          taskType,
          {
            title: i18n.tc('actions.staking.eth2.task.title'),
            numericKeys: []
          }
        );

        set(details, Eth2Details.parse(result));
      } catch (e: any) {
        logger.error(e);
        notify({
          title: i18n.tc('actions.staking.eth2.error.title'),
          message: i18n.tc(
            'actions.staking.eth2.error.description',
            undefined,
            {
              error: e.message
            }
          ),
          display: true
        });
        resetStatus();
      }
      setStatus(Status.LOADED);
    }

    async function fetchDeposits() {
      const secondarySection = Section.STAKING_ETH2_DEPOSITS;
      setStatus(newStatus, secondarySection);

      try {
        const taskType = TaskType.STAKING_ETH2_DEPOSITS;
        const { taskId } = await api.eth2StakingDeposits();
        const { result } = await awaitTask<Eth2Deposits, TaskMeta>(
          taskId,
          taskType,
          {
            title: `${i18n.t('actions.staking.eth2_deposits.task.title')}`,
            numericKeys: []
          }
        );

        set(deposits, Eth2Deposits.parse(result));
      } catch (e: any) {
        logger.error(e);
        notify({
          title: `${i18n.t('actions.staking.eth2_deposits.error.title')}`,
          message: `${i18n.t(
            'actions.staking.eth2_deposits.error.description',
            {
              error: e.message
            }
          )}`,
          display: true
        });
      }
      setStatus(Status.LOADED, secondarySection);
    }

    await Promise.allSettled([fetchDetails(), fetchDeposits()]);
  };

  const fetchDailyStats = async (refresh: boolean = false) => {
    if (!get(premium)) {
      return;
    }

    const taskType = TaskType.STAKING_ETH2_STATS;
    const { setStatus, loading, isFirstLoad, resetStatus } = getStatusUpdater(
      Section.STAKING_ETH2_STATS
    );

    const fetchStats = async (parameters?: Partial<Eth2DailyStatsPayload>) => {
      const defaults: Eth2DailyStatsPayload = {
        limit: 0,
        offset: 0,
        ascending: false,
        orderByAttribute: 'timestamp'
      };

      const params = Object.assign(defaults, parameters);

      if (params.onlyCache) {
        return await api.eth2Stats(params);
      }

      const { taskId } = await api.eth2StatsTask(defaults);

      const taskMeta: TaskMeta = {
        title: i18n.t('actions.eth2_staking_stats.task.title').toString(),
        description: i18n
          .t('actions.eth2_staking_stats.task.description')
          .toString(),
        numericKeys: []
      };

      const { result } = await awaitTask<Eth2DailyStats, TaskMeta>(
        taskId,
        taskType,
        taskMeta,
        true
      );
      return Eth2DailyStats.parse(result);
    };

    async function loadPage(payload: Eth2DailyStatsPayload) {
      const cacheParams = { ...payload, onlyCache: true };
      set(stats, await fetchStats(cacheParams));
    }

    try {
      const firstLoad = isFirstLoad();
      if (get(isTaskRunning(taskType)) || (loading() && !refresh)) {
        return;
      }

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      if (refresh || firstLoad) {
        if (firstLoad) {
          await loadPage(get(pagination));
        }
        setStatus(Status.REFRESHING);
        await fetchStats();
      }
      await loadPage(get(pagination));

      setStatus(
        get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
      );
    } catch (e: any) {
      logger.error(e);
      resetStatus();
      notify({
        title: i18n.t('actions.eth2_staking_stats.error.title').toString(),
        message: i18n
          .t('actions.eth2_staking_stats.error.message', { message: e.message })
          .toString(),
        display: true
      });
    }
  };

  const updatePagination = async (data: Eth2DailyStatsPayload) => {
    set(pagination, data);
    await fetchDailyStats();
  };

  const load = async (refresh: boolean = false) => {
    await Promise.allSettled([
      fetchStakingDetails(refresh),
      fetchDailyStats(refresh)
    ]);
  };

  const reset = () => {
    set(deposits, []);
    set(details, []);
    set(stats, defaultStats());
    set(pagination, defaultPagination());

    const { resetStatus } = getStatusUpdater(Section.STAKING_ETH2);
    resetStatus();
    resetStatus(Section.STAKING_ETH2_DEPOSITS);
    resetStatus(Section.STAKING_ETH2_STATS);
  };

  return {
    deposits,
    details,
    stats,
    updatePagination,
    load,
    reset
  };
});

const namespaced: boolean = true;

export const staking: Module<StakingState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useEth2StakingStore, import.meta.hot));
}
