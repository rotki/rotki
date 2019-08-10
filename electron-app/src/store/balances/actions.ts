import { ActionTree } from 'vuex';
import { RotkehlchenState } from '@/store';
import { BalanceState } from '@/store/balances/state';
import { service } from '@/services/rotkehlchen_service';
import { createTask, TaskType } from '@/model/task';

export const actions: ActionTree<BalanceState, RotkehlchenState> = {
  consume({ commit, getters }): any {},
  fetchExchangeBalances({ commit }, payload: ExchangeBalancePayload): void {
    const { name, balanceTask } = payload;
    service
      .query_exchange_balances_async(name)
      .then(result => {
        console.log(`Query ${name} returned task id ${result.task_id}`);
        const task = createTask(
          result.task_id,
          TaskType.QUERY_EXCHANGE_BALANCES,
          `Query ${name} Balances`,
          true
        );

        if (balanceTask) {
          commit('tasks/addBalanceTask', task);
        } else {
          commit('task/add', task);
        }
      })
      .catch(reason => {
        console.log(`Error at querying exchange ${name} balances: ${reason}`);
      });
  }
};

export interface ExchangeBalancePayload {
  readonly name: string;
  readonly balanceTask: boolean;
}

export const createExchangePayload: (
  name: string,
  balanceTask?: boolean
) => ExchangeBalancePayload = (name, balanceTask = false) => ({
  name,
  balanceTask
});
