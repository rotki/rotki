import { AdexBalances, AdexHistory } from '@rotki/common/lib/staking/adex';
import {
  Eth2DailyStats,
  Eth2DailyStatsPayload,
  Eth2Deposits,
  Eth2Details
} from '@rotki/common/lib/staking/eth2';
import { omitBy } from 'lodash';
import isEqual from 'lodash/isEqual';
import { usePremium } from '@/composables/premium';
import { useStatusUpdater } from '@/composables/status';
import { balanceKeys } from '@/services/consts';
import { useAdexApi } from '@/services/staking/adex';
import { useEth2Api } from '@/services/staking/eth2';
import { useNotifications } from '@/store/notifications';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { getStatus, setStatus } from '@/store/status';
import { useTasks } from '@/store/tasks';
import { isLoading } from '@/store/utils';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { Zero } from '@/utils/bignumbers';
import { logger } from '@/utils/logging';

const defaultStats = () => ({
  entries: [],
  entriesFound: 0,
  entriesTotal: 0,
  sumPnl: Zero,
  sumUsdValue: Zero
});

const defaultPagination = (): Eth2DailyStatsPayload => {
  const store = useFrontendSettingsStore();
  const itemsPerPage = store.itemsPerPage;

  return {
    limit: itemsPerPage,
    offset: 0,
    orderByAttributes: ['timestamp'],
    ascending: [false]
  };
};

export const useEth2StakingStore = defineStore('staking/eth2', () => {
  const deposits = ref<Eth2Deposits>([]);
  const details = ref<Eth2Details>([]);
  const stats = ref<Eth2DailyStats>(defaultStats());
  const pagination = ref<Eth2DailyStatsPayload>(defaultPagination());
  const premium = usePremium();
  const { awaitTask, isTaskRunning } = useTasks();
  const { notify } = useNotifications();
  const { t, tc } = useI18n();

  const api = useEth2Api();

  const fetchStakingDetails = async (refresh: boolean = false) => {
    if (!get(premium)) {
      return;
    }

    const { setStatus, loading, getStatus, resetStatus } = useStatusUpdater(
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
            title: tc('actions.staking.eth2.task.title'),
            numericKeys: []
          }
        );

        set(details, Eth2Details.parse(result));
      } catch (e: any) {
        logger.error(e);
        notify({
          title: tc('actions.staking.eth2.error.title'),
          message: tc('actions.staking.eth2.error.description', undefined, {
            error: e.message
          }),
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
            title: `${t('actions.staking.eth2_deposits.task.title')}`,
            numericKeys: []
          }
        );

        set(deposits, Eth2Deposits.parse(result));
      } catch (e: any) {
        logger.error(e);
        notify({
          title: `${t('actions.staking.eth2_deposits.error.title')}`,
          message: `${t('actions.staking.eth2_deposits.error.description', {
            error: e.message
          })}`,
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
    const { setStatus, loading, isFirstLoad, resetStatus } = useStatusUpdater(
      Section.STAKING_ETH2_STATS
    );

    const fetchStats = async (onlyCache: boolean) => {
      const defaults: Eth2DailyStatsPayload = {
        limit: 0,
        offset: 0,
        ascending: [false],
        orderByAttributes: ['timestamp'],
        onlyCache
      };

      const payload = Object.assign(defaults, {
        ...get(pagination),
        onlyCache
      });

      if (onlyCache) {
        return await api.eth2Stats(payload);
      }

      const { taskId } = await api.eth2StatsTask(defaults);

      const taskMeta: TaskMeta = {
        title: t('actions.eth2_staking_stats.task.title').toString(),
        description: t(
          'actions.eth2_staking_stats.task.description'
        ).toString(),
        numericKeys: []
      };

      const { result } = await awaitTask<Eth2DailyStats, TaskMeta>(
        taskId,
        taskType,
        taskMeta,
        true
      );

      setStatus(
        get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
      );

      return Eth2DailyStats.parse(result);
    };

    try {
      const firstLoad = isFirstLoad();
      const onlyCache = firstLoad ? false : !refresh;
      if ((get(isTaskRunning(taskType)) || loading()) && !onlyCache) {
        return;
      }

      const fetchOnlyCache = async () => {
        set(stats, await fetchStats(true));
      };

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      await fetchOnlyCache();

      if (!onlyCache) {
        setStatus(Status.REFRESHING);
        await fetchStats(false);
        await fetchOnlyCache();
      }

      setStatus(
        get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
      );
    } catch (e: any) {
      logger.error(e);
      resetStatus();
      notify({
        title: t('actions.eth2_staking_stats.error.title').toString(),
        message: t('actions.eth2_staking_stats.error.message', {
          message: e.message
        }).toString(),
        display: true
      });
    }
  };

  const updatePagination = async (data: Eth2DailyStatsPayload) => {
    const filteredData = omitBy(data, value => value === undefined);
    if (!isEqual(get(pagination), filteredData)) {
      set(pagination, filteredData);
      await fetchDailyStats();
    }
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

    const { resetStatus } = useStatusUpdater(Section.STAKING_ETH2);
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

export const useAdexStakingStore = defineStore('staking/adex', () => {
  const adexBalances = ref<AdexBalances>({});
  const adexHistory = ref<AdexHistory>({});

  const premium = usePremium();
  const { notify } = useNotifications();
  const { awaitTask } = useTasks();
  const { t } = useI18n();

  const api = useAdexApi();

  const fetchAdex = async (refresh: boolean) => {
    if (!get(premium)) {
      return;
    }

    const section = Section.STAKING_ADEX;
    const currentStatus = getStatus(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);

    try {
      const taskType = TaskType.STAKING_ADEX;
      const { taskId } = await api.adexBalances();
      const { result } = await awaitTask<AdexBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: `${t('actions.staking.adex_balances.task.title')}`,
          numericKeys: balanceKeys
        }
      );
      set(adexBalances, result);
    } catch (e: any) {
      notify({
        title: `${t('actions.staking.adex_balances.error.title')}`,
        message: `${t('actions.staking.adex_balances.error.description', {
          error: e.message
        })}`,
        display: true
      });
    }
    setStatus(Status.LOADED, section);

    const secondarySection = Section.STAKING_ADEX_HISTORY;
    setStatus(newStatus, secondarySection);

    try {
      const taskType = TaskType.STAKING_ADEX_HISTORY;
      const { taskId } = await api.adexHistory();
      const { result } = await awaitTask<AdexHistory, TaskMeta>(
        taskId,
        taskType,
        {
          title: `${t('actions.staking.adex_history.task.title')}`,
          numericKeys: [...balanceKeys, 'total_staked_amount']
        }
      );

      set(adexHistory, result);
    } catch (e: any) {
      notify({
        title: `${t('actions.staking.adex_history.error.title')}`,
        message: `${t('actions.staking.adex_history.error.description', {
          error: e.message
        })}`,
        display: true
      });
    }
    setStatus(Status.LOADED, secondarySection);
  };

  const reset = () => {
    set(adexBalances, {});
    set(adexHistory, {});
    setStatus(Status.NONE, Section.STAKING_ADEX);
    setStatus(Status.NONE, Section.STAKING_ADEX_HISTORY);
  };

  return {
    adexBalances,
    adexHistory,
    fetchAdex,
    reset
  };
});

export const useStakingStore = defineStore('staking', () => {
  const { reset: resetEth2 } = useEth2StakingStore();
  const { reset: resetAdex } = useAdexStakingStore();

  const reset = (module?: Module) => {
    if (!module || module === Module.ETH2) {
      resetEth2();
    }
    if (!module || module === Module.ADEX) {
      resetAdex();
    }
  };

  return {
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useEth2StakingStore, import.meta.hot));
  import.meta.hot.accept(acceptHMRUpdate(useAdexStakingStore, import.meta.hot));
}
