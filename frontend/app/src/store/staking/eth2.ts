import {
  Eth2DailyStats,
  type Eth2DailyStatsPayload,
  Eth2Deposits,
  Eth2Details
} from '@rotki/common/lib/staking/eth2';
import omitBy from 'lodash/omitBy';
import isEqual from 'lodash/isEqual';
import { Section, Status } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { Zero } from '@/utils/bignumbers';
import { logger } from '@/utils/logging';

const defaultStats = (): Eth2DailyStats => ({
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
  const { awaitTask, isTaskRunning } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { t, tc } = useI18n();

  const api = useEth2Api();

  const fetchStakingDetails = async (refresh = false): Promise<void> => {
    if (!get(premium)) {
      return;
    }

    const { setStatus, resetStatus, fetchDisabled } = useStatusUpdater(
      Section.STAKING_ETH2
    );

    if (fetchDisabled(refresh)) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;

    async function fetchDetails(): Promise<void> {
      setStatus(newStatus);
      try {
        const taskType = TaskType.STAKING_ETH2;
        const { taskId } = await api.eth2StakingDetails();
        const { result } = await awaitTask<Eth2Details, TaskMeta>(
          taskId,
          taskType,
          {
            title: tc('actions.staking.eth2.task.title')
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

    async function fetchDeposits(): Promise<void> {
      const secondarySection = Section.STAKING_ETH2_DEPOSITS;
      setStatus(newStatus, secondarySection);

      try {
        const taskType = TaskType.STAKING_ETH2_DEPOSITS;
        const { taskId } = await api.eth2StakingDeposits();
        const { result } = await awaitTask<Eth2Deposits, TaskMeta>(
          taskId,
          taskType,
          {
            title: `${t('actions.staking.eth2_deposits.task.title')}`
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

  const fetchDailyStats = async (refresh = false): Promise<void> => {
    if (!get(premium)) {
      return;
    }

    const taskType = TaskType.STAKING_ETH2_STATS;
    const { setStatus, loading, isFirstLoad, resetStatus } = useStatusUpdater(
      Section.STAKING_ETH2_STATS
    );

    const fetchStats = async (onlyCache: boolean): Promise<Eth2DailyStats> => {
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
        description: t('actions.eth2_staking_stats.task.description').toString()
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

      const fetchOnlyCache = async (): Promise<void> => {
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

  const updatePagination = async (
    data: Eth2DailyStatsPayload
  ): Promise<void> => {
    const filteredData = omitBy(data, value => value === undefined);
    if (!isEqual(get(pagination), filteredData)) {
      set(pagination, filteredData);
      await fetchDailyStats();
    }
  };

  const load = async (refresh = false): Promise<void> => {
    await Promise.allSettled([
      fetchStakingDetails(refresh),
      fetchDailyStats(refresh)
    ]);
  };

  const reset = (): void => {
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

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useEth2StakingStore, import.meta.hot));
}
