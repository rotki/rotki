import { Transaction } from 'electron';
import { ActionTree } from 'vuex';
import { exchangeName } from '@/components/history/consts';
import { EXCHANGE_CRYPTOCOM, TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import i18n from '@/i18n';
import { createTask, taskCompletion, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import { balanceKeys } from '@/services/consts';
import {
  movementNumericKeys,
  tradeNumericKeys,
  transactionNumericKeys
} from '@/services/history/const';
import {
  AssetMovement,
  EthTransaction,
  NewTrade,
  Trade,
  TradeLocation,
  TradeUpdate
} from '@/services/history/types';
import { api } from '@/services/rotkehlchen-api';
import { LimitedResponse } from '@/services/types-api';
import { Section, Status } from '@/store/const';
import {
  ACTION_ADD_LEDGER_ACTION,
  ACTION_DELETE_LEDGER_ACTION,
  ACTION_EDIT_LEDGER_ACTION,
  ACTION_FETCH_LEDGER_ACTIONS,
  MOVEMENTS,
  MUTATION_ADD_LEDGER_ACTION,
  MUTATION_SET_LEDGER_ACTIONS,
  TRADES,
  TRANSACTIONS
} from '@/store/history/consts';
import {
  AccountRequestMeta,
  AssetMovements,
  EthTransactions,
  HistoryState,
  IgnoreActionPayload,
  Trades,
  LedgerAction,
  LocationRequestMeta
} from '@/store/history/types';
import { Severity } from '@/store/notifications/consts';
import { NotificationPayload } from '@/store/notifications/types';
import { notify } from '@/store/notifications/utils';
import {
  ActionStatus,
  Message,
  RotkehlchenState,
  StatusPayload
} from '@/store/types';
import { Writeable } from '@/types';

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

    const section = Section.TRADES;
    const currentStatus = status(section);

    if (
      currentStatus === Status.LOADING ||
      currentStatus === Status.PARTIALLY_LOADED ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const setStatus: (newStatus: Status) => void = newStatus => {
      if (status(section) === newStatus) {
        return;
      }
      const payload: StatusPayload = {
        section: section,
        status: newStatus
      };
      commit('setStatus', payload, { root: true });
    };

    setStatus(refresh ? Status.REFRESHING : Status.LOADING);

    const { connectedExchanges } = balances!;
    const locations: TradeLocation[] = [
      ...connectedExchanges,
      TRADE_LOCATION_EXTERNAL,
      EXCHANGE_CRYPTOCOM
    ];

    const fetchLocation: (
      location: TradeLocation
    ) => Promise<void> = async location => {
      const { taskId } = await api.history.trades(location);
      const task = createTask<LocationRequestMeta>(taskId, taskType, {
        title: i18n.tc('actions.trades.task.title'),
        description: i18n.tc('actions.trades.task.description', undefined, {
          exchange: exchangeName(location)
        }),
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
      setStatus(Status.PARTIALLY_LOADED);
    };

    commit('resetTrades');

    const onError: (location: TradeLocation, message: string) => void = (
      location,
      message
    ) => {
      const exchange = exchangeName(location);
      notify(
        i18n.tc('actions.trades.error.description', undefined, {
          exchange,
          error: message
        }),
        i18n.tc('actions.trades.error.title', undefined, {
          exchange
        }),
        Severity.ERROR,
        true
      );
    };

    await Promise.all(
      locations.map(location =>
        fetchLocation(location).catch(e => onError(location, e))
      )
    );

    setStatus(Status.LOADED);
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

    const section = Section.ASSET_MOVEMENT;
    const currentStatus = status(section);

    if (
      currentStatus === Status.LOADING ||
      currentStatus === Status.PARTIALLY_LOADED ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const setStatus: (newStatus: Status) => void = newStatus => {
      if (status(section) === newStatus) {
        return;
      }
      const payload: StatusPayload = {
        section: section,
        status: newStatus
      };
      commit('setStatus', payload, { root: true });
    };

    setStatus(refresh ? Status.REFRESHING : Status.LOADING);

    const { connectedExchanges: locations } = balances!;

    const fetchLocation: (
      location: TradeLocation
    ) => Promise<void> = async location => {
      const { taskId } = await api.history.assetMovements(location);
      const task = createTask<LocationRequestMeta>(taskId, taskType, {
        title: i18n.tc('actions.asset_movements.task.title'),
        description: i18n.tc(
          'actions.asset_movements.task.description',
          undefined,
          {
            exchange: exchangeName(location)
          }
        ),
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
      setStatus(Status.PARTIALLY_LOADED);
    };

    commit('resetMovements');

    const onError: (location: TradeLocation, message: string) => void = (
      location,
      message
    ) => {
      const exchange = exchangeName(location);
      notify(
        i18n.tc('actions.asset_movements.error.description', undefined, {
          exchange,
          error: message
        }),
        i18n.tc('actions.asset_movements.error.title', undefined, { exchange }),
        Severity.ERROR,
        true
      );
    };

    await Promise.all(
      ([...locations, EXCHANGE_CRYPTOCOM] as TradeLocation[]).map(location =>
        fetchLocation(location).catch(e => onError(location, e.message))
      )
    );

    setStatus(Status.LOADED);
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

    const section = Section.TX;
    const currentStatus = status(section);

    if (
      currentStatus === Status.LOADING ||
      currentStatus === Status.PARTIALLY_LOADED ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }
    const setStatus: (newStatus: Status) => void = newStatus => {
      if (status(section) === newStatus) {
        return;
      }
      const payload: StatusPayload = {
        section: section,
        status: newStatus
      };
      commit('setStatus', payload, { root: true });
    };

    setStatus(refresh ? Status.REFRESHING : Status.LOADING);

    const { ethAccounts } = balances!;
    const addresses = ethAccounts.map(address => address.address);

    const fetchAddress: (address: string) => Promise<void> = async address => {
      const { taskId } = await api.history.ethTransactions(address);
      const task = createTask<AccountRequestMeta>(taskId, taskType, {
        title: i18n.tc('actions.transactions.task.title'),
        description: i18n.tc(
          'actions.transactions.task.description',
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
      setStatus(Status.PARTIALLY_LOADED);
    };

    commit('resetTransactions');

    const onError: (address: string, message: string) => void = (
      address,
      message
    ) => {
      notify(
        i18n.tc('actions.transactions.error.description', undefined, {
          error: message,
          address
        }),
        i18n.tc('actions.transactions.error.title'),
        Severity.ERROR,
        true
      );
    };

    await Promise.all(
      addresses.map(address =>
        fetchAddress(address).catch(e => onError(address, e.message))
      )
    );

    setStatus(Status.LOADED);
  },

  async [ACTION_FETCH_LEDGER_ACTIONS](
    {
      commit,
      dispatch,
      rootGetters: { 'tasks/isTaskRunning': isTaskRunning, status }
    },
    refresh: boolean
  ): Promise<void> {
    const taskType = TaskType.LEDGER_ACTIONS;
    if (isTaskRunning(taskType)) {
      return;
    }

    const section = Section.LEDGER_ACTIONS;
    const currentStatus = status(section);

    if (
      currentStatus === Status.LOADING ||
      currentStatus === Status.PARTIALLY_LOADED ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }
    const setStatus: (newStatus: Status) => void = newStatus => {
      if (status(section) === newStatus) {
        return;
      }
      const payload: StatusPayload = {
        section: section,
        status: newStatus
      };
      commit('setStatus', payload, { root: true });
    };

    setStatus(refresh ? Status.REFRESHING : Status.LOADING);

    try {
      const { taskId } = await api.history.ledgerActions();
      const task = createTask<TaskMeta>(taskId, taskType, {
        title: i18n.t('actions.ledger_actions.task.title').toString(),
        description: i18n
          .t('actions.ledger_actions.task.description', {})
          .toString(),
        ignoreResult: false,
        numericKeys: balanceKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<
        LimitedResponse<LedgerAction[]>,
        TaskMeta
      >(taskType, `${taskId}`);
      commit(MUTATION_SET_LEDGER_ACTIONS, result);
    } catch (e) {
      const message = i18n
        .t('actions.ledger_actions.error.description', {
          error: e.message
        })
        .toString();
      const title = i18n.t('actions.ledger_actions.error.title').toString();

      await dispatch(
        'notifications/notify',
        {
          title,
          message: message,
          severity: Severity.ERROR,
          display: true
        } as NotificationPayload,
        { root: true }
      );
    } finally {
      setStatus(Status.LOADED);
    }
  },

  async [ACTION_ADD_LEDGER_ACTION](
    { commit },
    action: Omit<LedgerAction, 'identifier'>
  ): Promise<ActionStatus> {
    try {
      const { identifier } = await api.history.addLedgerAction(action);
      commit(MUTATION_ADD_LEDGER_ACTION, {
        ...action,
        identifier
      } as LedgerAction);
      return { success: true };
    } catch (e) {
      return { success: false, message: e.message };
    }
  },

  async [ACTION_EDIT_LEDGER_ACTION](
    { commit },
    action: LedgerAction
  ): Promise<ActionStatus> {
    try {
      const result = await api.history.editLedgerAction(action);
      commit(MUTATION_SET_LEDGER_ACTIONS, result);
      return { success: true };
    } catch (e) {
      return { success: false, message: e.message };
    }
  },

  async [ACTION_DELETE_LEDGER_ACTION](
    { commit },
    identifier: number
  ): Promise<ActionStatus> {
    try {
      const result = await api.history.deleteLedgerAction(identifier);
      commit(MUTATION_SET_LEDGER_ACTIONS, result);
      return { success: true };
    } catch (e) {
      return { success: false, message: e.message };
    }
  },

  async ignoreActions(
    { commit, state },
    { actionIds, type }: IgnoreActionPayload
  ): Promise<ActionStatus> {
    let strings: string[] = [];
    try {
      strings = await api.ignoreActions(actionIds);
    } catch (e) {
      commit(
        'setMessage',
        {
          success: false,
          title: i18n.t('actions.ignore.error.title').toString(),
          description: i18n
            .t('actions.ignore.error.description', { error: e.message })
            .toString()
        } as Message,
        { root: true }
      );
      return { success: false };
    }

    if (type === TRADES) {
      const data = [...state.trades.data];

      for (let i = 0; i < data.length; i++) {
        const trade: Writeable<Trade> = data[i];
        if (strings.includes(trade.tradeId)) {
          data[i] = { ...data[i], ignoredInAccounting: true };
        }
      }
      commit('setTrades', {
        data,
        found: state.trades.found,
        limit: state.trades.limit
      } as Trades);
    } else if (type === MOVEMENTS) {
      const data = [...state.assetMovements.data];

      for (let i = 0; i < data.length; i++) {
        const movement: Writeable<AssetMovement> = data[i];
        if (strings.includes(movement.identifier)) {
          data[i] = { ...data[i], ignoredInAccounting: true };
        }
      }
      commit('setMovements', {
        data,
        found: state.assetMovements.found,
        limit: state.assetMovements.limit
      } as AssetMovements);
    } else if (type === TRANSACTIONS) {
      const data = [...state.transactions.data];

      for (let i = 0; i < data.length; i++) {
        const transaction: Writeable<EthTransaction> = data[i];
        if (strings.includes(transaction.txHash)) {
          data[i] = { ...data[i], ignoredInAccounting: true };
        }
      }
      commit('setTransactions', {
        data,
        found: state.transactions.found,
        limit: state.transactions.limit
      } as EthTransactions);
    }
    return { success: true };
  },
  async unignoreActions(
    { commit, state },
    { actionIds, type }: IgnoreActionPayload
  ) {
    let strings: string[] = [];
    try {
      strings = await api.unignoreActions(actionIds);
    } catch (e) {
      commit(
        'setMessage',
        {
          success: false,
          title: i18n.t('actions.unignore.error.title').toString(),
          description: i18n
            .t('actions.unignore.error.description', { error: e.message })
            .toString()
        } as Message,
        { root: true }
      );
      return { success: false };
    }
    if (type === TRADES) {
      const data = [...state.trades.data];

      for (let i = 0; i < data.length; i++) {
        const trade: Writeable<Trade> = data[i];
        if (!trade.ignoredInAccounting) {
          continue;
        }
        if (!strings.includes(trade.tradeId)) {
          data[i] = { ...data[i], ignoredInAccounting: false };
        }
      }
      commit('setTrades', {
        data,
        found: state.trades.found,
        limit: state.trades.limit
      } as Trades);
    } else if (type === MOVEMENTS) {
      const data = [...state.assetMovements.data];

      for (let i = 0; i < data.length; i++) {
        const movement: Writeable<AssetMovement> = data[i];
        if (!movement.ignoredInAccounting) {
          continue;
        }
        if (!strings.includes(movement.identifier)) {
          data[i] = { ...data[i], ignoredInAccounting: false };
        }
      }
      commit('setMovements', {
        data,
        found: state.assetMovements.found,
        limit: state.assetMovements.limit
      } as AssetMovements);
    } else if (type === TRANSACTIONS) {
      const data = [...state.transactions.data];

      for (let i = 0; i < data.length; i++) {
        const transaction: Writeable<EthTransaction> = data[i];
        if (!transaction.ignoredInAccounting) {
          continue;
        }
        if (!strings.includes(transaction.txHash)) {
          data[i] = { ...data[i], ignoredInAccounting: false };
        }
      }
      commit('setTransactions', {
        data,
        found: state.transactions.found,
        limit: state.transactions.limit
      } as EthTransactions);
    }
    return { success: true };
  }
};
