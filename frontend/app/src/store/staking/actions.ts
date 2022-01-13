import { AdexBalances, AdexHistory } from '@rotki/common/lib/staking/adex';
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
  ADEX_HISTORY
} from '@/store/staking/consts';
import { useEth2StakingStore } from '@/store/staking/index';
import { StakingState } from '@/store/staking/types';
import { useTasks } from '@/store/tasks';
import { RotkehlchenState } from '@/store/types';
import { getStatus, isLoading, setStatus } from '@/store/utils';
import { Module } from '@/types/modules';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

export const actions: ActionTree<StakingState, RotkehlchenState> = {
  async fetchAdex({ commit, rootState: { session } }, refresh: boolean) {
    if (!session?.premium) {
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
    setStatus(Status.LOADED, secondarySection);
  },
  async [ACTION_PURGE_DATA](
    { commit },
    module: typeof Module.ETH2 | typeof Module.ADEX | typeof ALL_MODULES
  ) {
    const { reset: eth2Reset } = useEth2StakingStore();

    function clearAdex() {
      commit(ADEX_HISTORY, {});
      commit(ADEX_BALANCES, {});
      setStatus(Status.NONE, Section.STAKING_ADEX);
      setStatus(Status.NONE, Section.STAKING_ADEX_HISTORY);
    }

    if (module === Module.ETH2) {
      eth2Reset();
    } else if (module === Module.ADEX) {
      clearAdex();
    } else if (module === ALL_MODULES) {
      eth2Reset();
      clearAdex();
    }
  }
};
