import { ActionTree } from 'vuex';
import i18n from '@/i18n';
import { createTask, taskCompletion, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import { balanceKeys } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { Section, Status } from '@/store/const';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { Eth2Staking, StakingState } from '@/store/staking/types';
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

    if (isLoading(currentStatus) || currentStatus === Status.LOADED) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);

    try {
      const taskType = TaskType.STAKING_ETH2;
      const { taskId } = await api.eth2Staking();
      const task = createTask(taskId, taskType, {
        title: i18n.tc('actions.staking.eth2.task.title'),
        ignoreResult: false,
        numericKeys: balanceKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<Eth2Staking, TaskMeta>(taskType);

      commit('eth2', result);
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
};
