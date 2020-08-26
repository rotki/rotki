import { ActionTree } from 'vuex';
import i18n from '@/i18n';
import { createTask, taskCompletion, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import { api } from '@/services/rotkehlchen-api';
import { tradeNumericKeys } from '@/services/trades/const';
import {
  NewTrade,
  Trade,
  TradeLocation,
  TradeUpdate
} from '@/services/trades/types';
import { LimitedResponse } from '@/services/types-api';
import { Status } from '@/store/const';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { RotkehlchenState } from '@/store/store';
import { TradeMeta, TradesState } from '@/store/trades/types';
import { ActionStatus } from '@/store/types';

export const actions: ActionTree<TradesState, RotkehlchenState> = {
  async fetchTrades(
    {
      commit,
      state,
      rootGetters: { 'tasks/isTaskRunning': isTaskRunning },
      rootState: { balances }
    },
    refresh: boolean = false
  ): Promise<void> {
    const taskType = TaskType.TRADES;
    if (isTaskRunning(taskType)) {
      return;
    }

    if (
      state.status === Status.LOADING ||
      (state.status === Status.LOADED && !refresh)
    ) {
      return;
    }

    commit('status', refresh ? Status.REFRESHING : Status.LOADING);

    const { connectedExchanges } = balances!;
    const locations: TradeLocation[] = [...connectedExchanges, 'external'];

    const fetchLocation: (
      location: TradeLocation
    ) => Promise<void> = async location => {
      const { taskId } = await api.trades.trades(location);
      const task = createTask<TradeMeta>(taskId, taskType, {
        description: i18n.tc('actions.trades.task_description'),
        ignoreResult: false,
        location: locations[0],
        numericKeys: tradeNumericKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<
        LimitedResponse<Trade[]>,
        TaskMeta
      >(taskType, `${taskId}`);
      commit('appendTrades', result.entries);
      commit('updateLimit', result.entriesLimit);
      commit('updateTotal', result.entriesFound);
    };

    commit('reset');

    try {
      await Promise.all(locations.map(fetchLocation));
    } catch (e) {
      notify(
        i18n.tc('actions.trades.error.description', undefined, {
          error: e.message
        }),
        i18n.tc('actions.trades.error.title'),
        Severity.ERROR,
        true
      );
    }

    commit('status', Status.LOADED);
  },

  async addExternalTrade({ commit }, trade: NewTrade): Promise<ActionStatus> {
    let success = false;
    let message = '';
    try {
      commit('addTrade', await api.trades.addExternalTrade(trade));
      success = true;
    } catch (e) {
      message = e.message;
    }
    return { success, message };
  },

  async editExternalTrade({ commit }, trade: Trade): Promise<ActionStatus> {
    let success = false;
    let message = '';
    try {
      const updatedTrade = await api.trades.editExternalTrade(trade);
      const payload: TradeUpdate = {
        trade: updatedTrade,
        oldTradeId: trade.tradeId
      };
      commit('updateTrade', payload);
      success = true;
    } catch (e) {
      message = e.message;
    }
    return { success, message };
  },

  async deleteExternalTrade(
    { commit },
    tradeId: string
  ): Promise<ActionStatus> {
    let success = false;
    let message = '';
    try {
      success = await api.trades.deleteExternalTrade(tradeId);
      if (success) {
        commit('deleteTrade', tradeId);
      }
    } catch (e) {
      message = e.message;
    }
    return { success, message };
  }
};
