import { Transaction } from 'electron';
import { ActionTree } from 'vuex';
import i18n from '@/i18n';
import { createTask, taskCompletion, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import {
  movementNumericKeys,
  tradeNumericKeys,
  transactionNumericKeys
} from '@/services/history/const';
import {
  AssetMovement,
  NewTrade,
  Trade,
  TradeLocation,
  TradeUpdate
} from '@/services/history/types';
import { api } from '@/services/rotkehlchen-api';
import { LimitedResponse } from '@/services/types-api';
import { Section, Status } from '@/store/const';
import {
  LocationRequestMeta,
  HistoryState,
  AccountRequestMeta
} from '@/store/history/types';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { ActionStatus, RotkehlchenState, StatusPayload } from '@/store/types';

export const actions: ActionTree<HistoryState, RotkehlchenState> = {
  async fetchTrades(
    {
      commit,
      rootGetters: { 'tasks/isTaskRunning': isTaskRunning, status },
      rootState: { balances }
    },
    refresh: boolean = false
  ): Promise<void> {
    const taskType = TaskType.TRADES;
    if (isTaskRunning(taskType)) {
      return;
    }

    const currentStatus = status(Section.TRADES);

    if (
      currentStatus === Status.LOADING ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const loadingPayload: StatusPayload = {
      section: Section.TRADES,
      status: refresh ? Status.REFRESHING : Status.LOADING
    };
    commit('setStatus', loadingPayload, { root: true });

    const { connectedExchanges } = balances!;
    const locations: TradeLocation[] = [...connectedExchanges, 'external'];

    const fetchLocation: (
      location: TradeLocation
    ) => Promise<void> = async location => {
      const { taskId } = await api.history.trades(location);
      const task = createTask<LocationRequestMeta>(taskId, taskType, {
        description: i18n.tc('actions.trades.task_description'),
        ignoreResult: false,
        location: location,
        numericKeys: tradeNumericKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<
        LimitedResponse<Trade[]>,
        TaskMeta
      >(taskType, `${taskId}`);
      commit('appendTrades', result);
    };

    commit('resetTrades');

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

    const loadedPayload: StatusPayload = {
      section: Section.TRADES,
      status: Status.LOADED
    };
    commit('setStatus', loadedPayload, { root: true });
  },

  async addExternalTrade({ commit }, trade: NewTrade): Promise<ActionStatus> {
    let success = false;
    let message = '';
    try {
      commit('addTrade', await api.history.addExternalTrade(trade));
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
      const updatedTrade = await api.history.editExternalTrade(trade);
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
      success = await api.history.deleteExternalTrade(tradeId);
      if (success) {
        commit('deleteTrade', tradeId);
      }
    } catch (e) {
      message = e.message;
    }
    return { success, message };
  },
  async fetchMovements(
    {
      commit,
      rootGetters: { 'tasks/isTaskRunning': isTaskRunning, status },
      rootState: { balances }
    },
    refresh: boolean = false
  ): Promise<void> {
    const taskType = TaskType.MOVEMENTS;
    if (isTaskRunning(taskType)) {
      return;
    }

    const currentStatus = status(Section.ASSET_MOVEMENT);

    if (
      currentStatus === Status.LOADING ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const payload: StatusPayload = {
      section: Section.ASSET_MOVEMENT,
      status: refresh ? Status.REFRESHING : Status.LOADING
    };

    commit('setStatus', payload, { root: true });

    const { connectedExchanges: locations } = balances!;

    const fetchLocation: (
      location: TradeLocation
    ) => Promise<void> = async location => {
      const { taskId } = await api.history.assetMovements(location);
      const task = createTask<LocationRequestMeta>(taskId, taskType, {
        description: i18n.tc('actions.asset_movements.task_description'),
        ignoreResult: false,
        location: location,
        numericKeys: movementNumericKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<
        LimitedResponse<AssetMovement[]>,
        TaskMeta
      >(taskType, `${taskId}`);
      commit('updateMovements', result);
    };

    commit('resetMovements');

    try {
      await Promise.all(locations.map(fetchLocation));
    } catch (e) {
      notify(
        i18n.tc('actions.asset_movements.error.description', undefined, {
          error: e.message
        }),
        i18n.tc('actions.asset_movements.error.title'),
        Severity.ERROR,
        true
      );
    }

    const loaded: StatusPayload = {
      section: Section.ASSET_MOVEMENT,
      status: Status.LOADED
    };
    commit('setStatus', loaded, { root: true });
  },

  async fetchTransactions(
    {
      commit,
      rootGetters: { 'tasks/isTaskRunning': isTaskRunning, status },
      rootState: { balances }
    },
    refresh: boolean = false
  ): Promise<void> {
    const taskType = TaskType.TX;
    if (isTaskRunning(taskType)) {
      return;
    }

    const currentStatus = status(Section.TX);

    if (
      currentStatus === Status.LOADING ||
      currentStatus === Status.PARTIALLY_LOADED ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const payload: StatusPayload = {
      section: Section.TX,
      status: refresh ? Status.REFRESHING : Status.LOADING
    };

    commit('setStatus', payload, { root: true });

    const { ethAccounts } = balances!;
    const addresses = Object.keys(ethAccounts);

    const fetchAddress: (address: string) => Promise<void> = async address => {
      const { taskId } = await api.history.ethTransactions(address);
      const task = createTask<AccountRequestMeta>(taskId, taskType, {
        description: i18n.tc(
          'actions.transactions.task_description',
          undefined,
          {
            address
          }
        ),
        ignoreResult: false,
        address: address,
        numericKeys: transactionNumericKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<
        LimitedResponse<Transaction[]>,
        AccountRequestMeta
      >(taskType, `${taskId}`);
      commit('updateTransactions', result);
    };

    commit('resetTransactions');

    try {
      await Promise.all(addresses.map(fetchAddress));
    } catch (e) {
      notify(
        i18n.tc('actions.transactions.error.description', undefined, {
          error: e.message
        }),
        i18n.tc('actions.transactions.error.title'),
        Severity.ERROR,
        true
      );
    }

    const loaded: StatusPayload = {
      section: Section.TX,
      status: Status.LOADED
    };
    commit('setStatus', loaded, { root: true });
  }
};
