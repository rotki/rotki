import { ActionTree } from 'vuex';
import i18n from '@/i18n';
import { createTask, taskCompletion, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import { balanceKeys } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { Section, Status } from '@/store/const';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import {
  AdexBalances,
  AdexEvents,
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

        commit('eth2Details', result);
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

        commit('eth2Deposits', result);
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

      commit('adexBalances', result);
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

    const secondarySection = Section.STAKING_ADEX_EVENTS;
    setStatus(newStatus, secondarySection, status, commit);
    try {
      const taskType = TaskType.STAKING_ADEX_EVENTS;
      const { taskId } = await api.adexEvents();
      const task = createTask(taskId, taskType, {
        title: `${i18n.t('actions.staking.adex_events.task.title')}`,
        ignoreResult: false,
        numericKeys: [...balanceKeys, 'total_staked_amount']
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<AdexEvents, TaskMeta>(taskType);

      commit('adexEvents', result);
    } catch (e) {
      notify(
        `${i18n.t('actions.staking.adex_events.error.description', {
          error: e.message
        })}`,
        `${i18n.t('actions.staking.adex_events.error.title')}`,
        Severity.ERROR,
        true
      );
    }
    setStatus(Status.LOADED, secondarySection, status, commit);
  }
};
