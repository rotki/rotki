import { ActionTree } from 'vuex';
import i18n from '@/i18n';
import { createTask, taskCompletion, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import { balanceKeys } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import {
  ALL_MODULES,
  MODULE_ADEX,
  MODULE_ETH2
} from '@/services/session/consts';
import { Section, Status } from '@/store/const';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import {
  ACTION_PURGE_DATA,
  ADEX_BALANCES,
  ADEX_HISTORY,
  ETH2_DEPOSITS,
  ETH2_DETAILS
} from '@/store/staking/consts';
import {
  AdexBalances,
  AdexHistory,
  Eth2Deposit,
  Eth2Detail,
  StakingState
} from '@/store/staking/types';
import { RotkehlchenState } from '@/store/types';
import { isLoading, setStatus } from '@/store/utils';

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

      try {
        const taskType = TaskType.STAKING_ETH2;
        const { taskId } = await api.eth2StakingDetails();
        const task = createTask(taskId, taskType, {
          title: i18n.tc('actions.staking.eth2.task.title'),
          ignoreResult: false,
          numericKeys: balanceKeys
        });

        commit('tasks/add', task, { root: true });

        const { result } = await taskCompletion<Eth2Detail[], TaskMeta>(
          taskType
        );

        commit(ETH2_DETAILS, result);
      } catch (e) {
        notify(
          i18n.tc('actions.staking.eth2.error.description', undefined, {
            error: e.message
          }),
          i18n.tc('actions.staking.eth2.error.title'),
          Severity.ERROR,
          true
        );
      }
      setStatus(Status.LOADED, section, status, commit);
    }

    async function fetchDeposits() {
      const secondarySection = Section.STAKING_ETH2_DEPOSITS;
      setStatus(newStatus, secondarySection, status, commit);

      try {
        const taskType = TaskType.STAKING_ETH2_DEPOSITS;
        const { taskId } = await api.eth2StakingDeposits();
        const task = createTask(taskId, taskType, {
          title: `${i18n.t('actions.staking.eth2_deposits.task.title')}`,
          ignoreResult: false,
          numericKeys: balanceKeys
        });

        commit('tasks/add', task, { root: true });

        const { result } = await taskCompletion<Eth2Deposit[], TaskMeta>(
          taskType
        );

        commit(ETH2_DEPOSITS, result);
      } catch (e) {
        notify(
          `${i18n.t('actions.staking.eth2_deposits.error.description', {
            error: e.message
          })}`,
          `${i18n.t('actions.staking.eth2_deposits.error.title')}`,
          Severity.ERROR,
          true
        );
      }
      setStatus(Status.LOADED, secondarySection, status, commit);
    }

    await Promise.all([fetchDetails(), fetchDeposits()]);
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

    try {
      const taskType = TaskType.STAKING_ADEX;
      const { taskId } = await api.adexBalances();
      const task = createTask(taskId, taskType, {
        title: `${i18n.t('actions.staking.adex_balances.task.title')}`,
        ignoreResult: false,
        numericKeys: balanceKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<AdexBalances, TaskMeta>(taskType);

      commit(ADEX_BALANCES, result);
    } catch (e) {
      notify(
        `${i18n.t('actions.staking.adex_balances.error.description', {
          error: e.message
        })}`,
        `${i18n.t('actions.staking.adex_balances.error.title')}`,
        Severity.ERROR,
        true
      );
    }
    setStatus(Status.LOADED, section, status, commit);

    const secondarySection = Section.STAKING_ADEX_HISTORY;
    setStatus(newStatus, secondarySection, status, commit);
    try {
      const taskType = TaskType.STAKING_ADEX_HISTORY;
      const { taskId } = await api.adexHistory();
      const task = createTask(taskId, taskType, {
        title: `${i18n.t('actions.staking.adex_history.task.title')}`,
        ignoreResult: false,
        numericKeys: [...balanceKeys, 'total_staked_amount']
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<AdexHistory, TaskMeta>(taskType);

      commit(ADEX_HISTORY, result);
    } catch (e) {
      notify(
        `${i18n.t('actions.staking.adex_history.error.description', {
          error: e.message
        })}`,
        `${i18n.t('actions.staking.adex_history.error.title')}`,
        Severity.ERROR,
        true
      );
    }
    setStatus(Status.LOADED, secondarySection, status, commit);
  },
  async [ACTION_PURGE_DATA](
    { commit, rootGetters: { status } },
    module: typeof MODULE_ETH2 | typeof MODULE_ADEX | typeof ALL_MODULES
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

    if (module === MODULE_ETH2) {
      clearEth2();
    } else if (module === MODULE_ADEX) {
      clearAdex();
    } else if (module === ALL_MODULES) {
      clearEth2();
      clearAdex();
    }
  }
};
