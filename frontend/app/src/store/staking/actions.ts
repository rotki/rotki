import { AdexBalances, AdexHistory } from '@rotki/common/lib/staking/adex';
import {
  Eth2DailyStats,
  Eth2DailyStatsPayload,
  Eth2Deposits,
  Eth2Details
} from '@rotki/common/lib/staking/eth2';
import { ActionTree } from 'vuex';
import i18n from '@/i18n';
import { balanceKeys } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { ALL_MODULES } from '@/services/session/consts';
import { Section, Status } from '@/store/const';
import { useNotifications } from '@/store/notifications';
import {
  ACTION_PURGE_DATA,
  ADEX_BALANCES,
  ADEX_HISTORY,
  ETH2_DAILY_STATS,
  ETH2_DEPOSITS,
  ETH2_DETAILS
} from '@/store/staking/consts';
import { StakingState } from '@/store/staking/types';
import { useTasks } from '@/store/tasks';
import { RotkehlchenState } from '@/store/types';
import { getStatusUpdater, isLoading, setStatus } from '@/store/utils';
import { Module } from '@/types/modules';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';

export const actions: ActionTree<StakingState, RotkehlchenState> = {
  async fetchStakingDetails(
    { commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean
  ) {
    if (!session?.premium) {
      return;
    }

    const section = Section.STAKING_ETH2;
    const currentStatus = status(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;

    async function fetchDetails() {
      setStatus(newStatus, section, status, commit);
      const { awaitTask } = useTasks();
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

        commit(ETH2_DETAILS, Eth2Details.parse(result));
      } catch (e: any) {
        logger.error(e);
        const { notify } = useNotifications();
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
      }
      setStatus(Status.LOADED, section, status, commit);
    }

    async function fetchDeposits() {
      const secondarySection = Section.STAKING_ETH2_DEPOSITS;
      setStatus(newStatus, secondarySection, status, commit);
      const { awaitTask } = useTasks();

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

        commit(ETH2_DEPOSITS, Eth2Deposits.parse(result));
      } catch (e: any) {
        logger.error(e);
        const { notify } = useNotifications();
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
      setStatus(Status.LOADED, secondarySection, status, commit);
    }

    await Promise.allSettled([fetchDetails(), fetchDeposits()]);
  },

  async fetchDailyStats(
    { commit, rootGetters: { status }, rootState: { session } },
    payload: Eth2DailyStatsPayload
  ) {
    if (!session?.premium) {
      return;
    }

    const taskType = TaskType.STAKING_ETH2_STATS;
    const { awaitTask, isTaskRunning } = useTasks();
    const { setStatus, loading, isFirstLoad } = getStatusUpdater(
      commit,
      Section.STAKING_ETH2_STATS,
      status
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
      const data = await fetchStats(cacheParams);
      commit(ETH2_DAILY_STATS, data);
    }

    try {
      const firstLoad = isFirstLoad();
      const onlyCache = firstLoad ? false : payload.onlyCache;
      if (isTaskRunning(taskType).value || (loading() && !onlyCache)) {
        return;
      }

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      if (!onlyCache) {
        if (firstLoad) {
          await loadPage(payload);
        }
        setStatus(Status.REFRESHING);
        await fetchStats();
      }
      await loadPage(payload);

      setStatus(
        isTaskRunning(taskType).value ? Status.REFRESHING : Status.LOADED
      );
    } catch (e: any) {
      logger.error(e);
      setStatus(Status.NONE);
      const { notify } = useNotifications();
      notify({
        title: i18n.t('actions.eth2_staking_stats.error.title').toString(),
        message: i18n
          .t('actions.eth2_staking_stats.error.message', { message: e.message })
          .toString(),
        display: true
      });
    }
  },

  async fetchAdex(
    { commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean
  ) {
    if (!session?.premium) {
      return;
    }

    const section = Section.STAKING_ADEX;
    const currentStatus = status(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);
    const { awaitTask } = useTasks();

    try {
      const taskType = TaskType.STAKING_ADEX;
      const { taskId } = await api.adexBalances();
      const { result } = await awaitTask<AdexBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: `${i18n.t('actions.staking.adex_balances.task.title')}`,
          numericKeys: balanceKeys
        }
      );

      commit(ADEX_BALANCES, result);
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: `${i18n.t('actions.staking.adex_balances.error.title')}`,
        message: `${i18n.t('actions.staking.adex_balances.error.description', {
          error: e.message
        })}`,
        display: true
      });
    }
    setStatus(Status.LOADED, section, status, commit);

    const secondarySection = Section.STAKING_ADEX_HISTORY;
    setStatus(newStatus, secondarySection, status, commit);

    try {
      const taskType = TaskType.STAKING_ADEX_HISTORY;
      const { taskId } = await api.adexHistory();
      const { result } = await awaitTask<AdexHistory, TaskMeta>(
        taskId,
        taskType,
        {
          title: `${i18n.t('actions.staking.adex_history.task.title')}`,
          numericKeys: [...balanceKeys, 'total_staked_amount']
        }
      );

      commit(ADEX_HISTORY, result);
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: `${i18n.t('actions.staking.adex_history.error.title')}`,
        message: `${i18n.t('actions.staking.adex_history.error.description', {
          error: e.message
        })}`,
        display: true
      });
    }
    setStatus(Status.LOADED, secondarySection, status, commit);
  },
  async [ACTION_PURGE_DATA](
    { commit, rootGetters: { status } },
    module: typeof Module.ETH2 | typeof Module.ADEX | typeof ALL_MODULES
  ) {
    function clearEth2() {
      commit(ETH2_DETAILS, []);
      commit(ETH2_DEPOSITS, []);
      setStatus(Status.NONE, Section.STAKING_ETH2, status, commit);
      setStatus(Status.NONE, Section.STAKING_ETH2_DEPOSITS, status, commit);
    }

    function clearAdex() {
      commit(ADEX_HISTORY, {});
      commit(ADEX_BALANCES, {});
      setStatus(Status.NONE, Section.STAKING_ADEX, status, commit);
      setStatus(Status.NONE, Section.STAKING_ADEX_HISTORY, status, commit);
    }

    if (module === Module.ETH2) {
      clearEth2();
    } else if (module === Module.ADEX) {
      clearAdex();
    } else if (module === ALL_MODULES) {
      clearEth2();
      clearAdex();
    }
  }
};
