import { ActionTree } from 'vuex';
import { RotkehlchenState } from '@/store/store';
import { TaskState } from '@/store/tasks/state';
import { BalanceStatus } from '@/enums/BalanceStatus';
import { api } from '@/services/rotkehlchen-api';
import { createTask, TaskType } from '@/model/task';

export const actions: ActionTree<TaskState, RotkehlchenState> = {
  removeTask({ state, commit }, taskId: number) {
    const balanceTasks = [...state.balanceTasks];

    for (let i = 0; i < balanceTasks.length; i++) {
      const taskId = balanceTasks[i];

      if (taskId === taskId) {
        if (state.queryStatus !== BalanceStatus.requested) {
          console.error({
            error: `BalanceStatus should only be requested at this point. But value is ${state.queryStatus}`
          });
          return;
        }

        balanceTasks.splice(i, 1);
        commit('removeBalanceTask', taskId);

        if (balanceTasks.length === 0) {
          commit('status', BalanceStatus.complete);

          api
            .queryBalancesAsync()
            .then(result => {
              const task = createTask(
                result.task_id,
                TaskType.QUERY_BALANCES,
                'Query All Balances'
              );
              commit('add', task);
            })
            .catch((reason: Error) => {
              console.error(
                `Error at querying all balances asynchronously: ${reason.message}`
              );
            });
        }
      }
    }
    commit('remove', taskId);
  }
};
