import { ActionTree } from 'vuex';
import { exchangeName } from '@/components/history/consts';
import { TRADE_LOCATION_EXTERNAL, EXTERNAL_EXCHANGES } from '@/data/defaults';
import i18n from '@/i18n';
import { createTask, taskCompletion, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import { SupportedExchange } from '@/services/balances/types';
import { balanceKeys } from '@/services/consts';
import {
  movementNumericKeys,
  tradeNumericKeys,
  transactionNumericKeys
} from '@/services/history/const';
import {
  AssetMovement,
  EthTransaction,
  GitcoinGrants,
  GitcoinGrantEventsPayload,
  NewTrade,
  Trade,
  TradeLocation,
  TradeUpdate
} from '@/services/history/types';
import { api } from '@/services/rotkehlchen-api';
import { ALL_CENTRALIZED_EXCHANGES } from '@/services/session/consts';
import {
  ActionResult,
  EntryWithMeta,
  LimitedResponse
} from '@/services/types-api';
import { Section, Status } from '@/store/const';
import {
  FETCH_FROM_CACHE,
  FETCH_FROM_SOURCE,
  FETCH_REFRESH,
  HistoryActions,
  HistoryMutations,
  IGNORE_LEDGER_ACTION,
  IGNORE_MOVEMENTS,
  IGNORE_TRADES,
  IGNORE_TRANSACTIONS
} from '@/store/history/consts';
import { defaultHistoricState } from '@/store/history/state';
import {
  AccountRequestMeta,
  AssetMovementEntry,
  AssetMovements,
  EthTransactionEntry,
  EthTransactions,
  FetchSource,
  HistoricData,
  HistoryState,
  IgnoreActionPayload,
  LedgerAction,
  LedgerActionEntry,
  LedgerActions,
  LocationRequestMeta,
  TradeEntry,
  Trades
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
import { setStatus } from '@/store/utils';
import { Writeable } from '@/types';
import { assert } from '@/utils/assertions';
import { uniqueStrings } from '@/utils/data';

export const actions: ActionTree<HistoryState, RotkehlchenState> = {
  async [HistoryActions.FETCH_TRADES](
    {
      commit,
      state,
      rootGetters: { 'tasks/isTaskRunning': isTaskRunning, status },
      rootState: { balances }
    },
    source: FetchSource
  ): Promise<void> {
    const taskType = TaskType.TRADES;
    if (isTaskRunning(taskType)) {
      return;
    }

    const section = Section.TRADES;
    const currentStatus = status(section);
    const refresh = source === FETCH_REFRESH || source === FETCH_FROM_SOURCE;

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
      ...(source !== FETCH_FROM_SOURCE
        ? ([TRADE_LOCATION_EXTERNAL, ...EXTERNAL_EXCHANGES] as TradeLocation[])
        : []),
      ...connectedExchanges.map(exchange => exchange.location)
    ];

    const fetchLocation: (
      location: TradeLocation
    ) => Promise<void> = async location => {
      const { taskId } = await api.history.trades(
        location,
        source === FETCH_FROM_CACHE
      );
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
        LimitedResponse<EntryWithMeta<Trade>>,
        TaskMeta
      >(taskType, `${taskId}`);

      const trades = [
        ...state.trades.data.filter(trade => trade.location !== location),
        ...result.entries.map(({ entry, ignoredInAccounting }) => ({
          ...entry,
          ignoredInAccounting
        }))
      ];
      const data: HistoricData<TradeEntry> = {
        data: trades,
        found: result.entriesFound,
        limit: result.entriesLimit
      };
      commit(HistoryMutations.SET_TRADES, data);
      setStatus(Status.PARTIALLY_LOADED);
    };

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

  async [HistoryActions.ADD_EXTERNAL_TRADE](
    { commit },
    trade: NewTrade
  ): Promise<ActionStatus> {
    let success = false;
    let message = '';
    try {
      commit(
        HistoryMutations.ADD_TRADE,
        await api.history.addExternalTrade(trade)
      );
      success = true;
    } catch (e) {
      message = e.message;
    }
    return { success, message };
  },

  async [HistoryActions.EDIT_EXTERNAL_TRADE](
    { commit },
    trade: TradeEntry
  ): Promise<ActionStatus> {
    let success = false;
    let message = '';
    try {
      const updatedTrade = await api.history.editExternalTrade(trade);
      const payload: TradeUpdate = {
        trade: {
          ...updatedTrade,
          ignoredInAccounting: trade.ignoredInAccounting
        },
        oldTradeId: trade.tradeId
      };
      commit(HistoryMutations.UPDATE_TRADE, payload);
      success = true;
    } catch (e) {
      message = e.message;
    }
    return { success, message };
  },

  async [HistoryActions.DELETE_EXTERNAL_TRADE](
    { commit },
    tradeId: string
  ): Promise<ActionStatus> {
    let success = false;
    let message = '';
    try {
      success = await api.history.deleteExternalTrade(tradeId);
      if (success) {
        commit(HistoryMutations.DELETE_TRADE, tradeId);
      }
    } catch (e) {
      message = e.message;
    }
    return { success, message };
  },
  async [HistoryActions.FETCH_MOVEMENTS](
    {
      commit,
      state,
      rootGetters: { 'tasks/isTaskRunning': isTaskRunning, status },
      rootState: { balances }
    },
    source: FetchSource
  ): Promise<void> {
    const taskType = TaskType.MOVEMENTS;
    if (isTaskRunning(taskType)) {
      return;
    }

    const section = Section.ASSET_MOVEMENT;
    const currentStatus = status(section);
    const refresh = source === FETCH_REFRESH || source === FETCH_FROM_SOURCE;

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

    const locations = balances!.connectedExchanges
      .map(({ location }) => location)
      .filter(uniqueStrings);

    const fetchLocation: (
      location: TradeLocation
    ) => Promise<void> = async location => {
      const { taskId } = await api.history.assetMovements(
        location,
        source === FETCH_FROM_CACHE
      );
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
        LimitedResponse<EntryWithMeta<AssetMovement>>,
        TaskMeta
      >(taskType, `${taskId}`);

      const movements = [
        ...state.assetMovements.data.filter(
          movement => movement.location !== location
        ),
        ...result.entries.map(({ entry, ignoredInAccounting }) => ({
          ...entry,
          ignoredInAccounting: ignoredInAccounting
        }))
      ];

      const data: HistoricData<AssetMovementEntry> = {
        data: movements,
        limit: result.entriesLimit,
        found: result.entriesFound
      };
      commit(HistoryMutations.SET_MOVEMENTS, data);
      setStatus(Status.PARTIALLY_LOADED);
    };

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
      ([
        ...(source !== FETCH_FROM_SOURCE ? EXTERNAL_EXCHANGES : []),
        ...locations
      ] as TradeLocation[]).map(location =>
        fetchLocation(location).catch(e => onError(location, e.message))
      )
    );

    setStatus(Status.LOADED);
  },

  async [HistoryActions.FETCH_TRANSACTIONS](
    {
      commit,
      state,
      rootGetters: { 'tasks/isTaskRunning': isTaskRunning, status },
      rootState: { balances }
    },
    source: FetchSource
  ): Promise<void> {
    const taskType = TaskType.TX;
    if (isTaskRunning(taskType)) {
      return;
    }

    const section = Section.TX;
    const currentStatus = status(section);
    const refresh = source === FETCH_REFRESH || source === FETCH_FROM_SOURCE;

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
      const { taskId } = await api.history.ethTransactions(
        address,
        source === FETCH_FROM_CACHE
      );
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
        LimitedResponse<EntryWithMeta<EthTransaction>>,
        AccountRequestMeta
      >(taskType, `${taskId}`);
      const newTransactions = result.entries.map(
        ({ entry, ignoredInAccounting }) => ({
          ...entry,
          ignoredInAccounting: ignoredInAccounting
        })
      );

      const transactions = [
        ...state.transactions.data.filter(
          tx => tx.fromAddress !== address && tx.toAddress !== address
        ),
        ...newTransactions
      ];
      const data: HistoricData<EthTransactionEntry> = {
        data: transactions,
        limit: result.entriesLimit,
        found: result.entriesFound
      };
      commit(HistoryMutations.SET_TRANSACTIONS, data);
      setStatus(Status.PARTIALLY_LOADED);
    };

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

  async [HistoryActions.FETCH_LEDGER_ACTIONS](
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
        numericKeys: [...balanceKeys, 'rate']
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<
        LimitedResponse<EntryWithMeta<LedgerAction>>,
        TaskMeta
      >(taskType, `${taskId}`);
      const data: HistoricData<LedgerActionEntry> = {
        data: result.entries.map(({ entry, ignoredInAccounting }) => ({
          ...entry,
          ignoredInAccounting
        })),
        limit: result.entriesLimit,
        found: result.entriesFound
      };
      commit(HistoryMutations.SET_LEDGER_ACTIONS, data);
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

  async [HistoryActions.ADD_LEDGER_ACTION](
    { commit },
    action: Omit<LedgerAction, 'identifier'>
  ): Promise<ActionStatus> {
    try {
      const { identifier } = await api.history.addLedgerAction(action);
      commit(HistoryMutations.ADD_LEDGER_ACTION, {
        ...action,
        identifier
      } as LedgerAction);
      return { success: true };
    } catch (e) {
      return { success: false, message: e.message };
    }
  },

  async [HistoryActions.EDIT_LEDGER_ACTION](
    { commit },
    action: LedgerAction
  ): Promise<ActionStatus> {
    try {
      const result = await api.history.editLedgerAction(action);
      const data: HistoricData<LedgerActionEntry> = {
        data: result.entries.map(({ entry, ignoredInAccounting }) => ({
          ...entry,
          ignoredInAccounting
        })),
        limit: result.entriesLimit,
        found: result.entriesFound
      };
      commit(HistoryMutations.SET_LEDGER_ACTIONS, data);
      return { success: true };
    } catch (e) {
      return { success: false, message: e.message };
    }
  },

  async [HistoryActions.DELETE_LEDGER_ACTION](
    { commit },
    identifier: number
  ): Promise<ActionStatus> {
    try {
      const result = await api.history.deleteLedgerAction(identifier);
      const data: HistoricData<LedgerActionEntry> = {
        data: result.entries.map(({ entry, ignoredInAccounting }) => ({
          ...entry,
          ignoredInAccounting
        })),
        limit: result.entriesLimit,
        found: result.entriesFound
      };
      commit(HistoryMutations.SET_LEDGER_ACTIONS, data);
      return { success: true };
    } catch (e) {
      return { success: false, message: e.message };
    }
  },

  async [HistoryActions.IGNORE_ACTIONS](
    { commit, state },
    { actionIds, type }: IgnoreActionPayload
  ): Promise<ActionStatus> {
    let strings: string[] = [];
    try {
      const result = await api.ignoreActions(actionIds, type);
      const entries = result[type];
      assert(entries, `expected entry for ${type} but there where non`);
      strings = entries;
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

    if (type === IGNORE_TRADES) {
      const data = [...state.trades.data];

      for (let i = 0; i < data.length; i++) {
        const trade: Writeable<TradeEntry> = data[i];
        if (strings.includes(trade.tradeId)) {
          data[i] = { ...data[i], ignoredInAccounting: true };
        }
      }
      commit(HistoryMutations.SET_TRADES, {
        data,
        found: state.trades.found,
        limit: state.trades.limit
      } as Trades);
    } else if (type === IGNORE_MOVEMENTS) {
      const data = [...state.assetMovements.data];

      for (let i = 0; i < data.length; i++) {
        const movement: Writeable<AssetMovementEntry> = data[i];
        if (strings.includes(movement.identifier)) {
          data[i] = { ...data[i], ignoredInAccounting: true };
        }
      }
      commit(HistoryMutations.SET_MOVEMENTS, {
        data,
        found: state.assetMovements.found,
        limit: state.assetMovements.limit
      } as AssetMovements);
    } else if (type === IGNORE_TRANSACTIONS) {
      const data = [...state.transactions.data];

      for (let i = 0; i < data.length; i++) {
        const transaction: Writeable<EthTransactionEntry> = data[i];
        const key =
          transaction.txHash + transaction.fromAddress + transaction.nonce;
        if (strings.includes(key)) {
          data[i] = { ...data[i], ignoredInAccounting: true };
        }
      }
      commit(HistoryMutations.SET_TRANSACTIONS, {
        data,
        found: state.transactions.found,
        limit: state.transactions.limit
      } as EthTransactions);
    } else if (type === IGNORE_LEDGER_ACTION) {
      const data = [...state.ledgerActions.data];

      for (let i = 0; i < data.length; i++) {
        const ledgerAction: Writeable<LedgerActionEntry> = data[i];

        if (strings.includes(ledgerAction.identifier.toString())) {
          data[i] = { ...data[i], ignoredInAccounting: true };
        }
      }
      commit(HistoryMutations.SET_LEDGER_ACTIONS, {
        data,
        found: state.ledgerActions.found,
        limit: state.ledgerActions.limit
      } as LedgerActions);
    }
    return { success: true };
  },
  async [HistoryActions.UNIGNORE_ACTION](
    { commit, state },
    { actionIds, type }: IgnoreActionPayload
  ) {
    let strings: string[] = [];
    try {
      const result = await api.unignoreActions(actionIds, type);
      strings = result[type] ?? [];
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
    if (type === IGNORE_TRADES) {
      const data = [...state.trades.data];

      for (let i = 0; i < data.length; i++) {
        const trade: Writeable<TradeEntry> = data[i];
        if (!trade.ignoredInAccounting) {
          continue;
        }
        if (!strings.includes(trade.tradeId)) {
          data[i] = { ...data[i], ignoredInAccounting: false };
        }
      }
      commit(HistoryMutations.SET_TRADES, {
        data,
        found: state.trades.found,
        limit: state.trades.limit
      } as Trades);
    } else if (type === IGNORE_MOVEMENTS) {
      const data = [...state.assetMovements.data];

      for (let i = 0; i < data.length; i++) {
        const movement: Writeable<AssetMovementEntry> = data[i];
        if (!movement.ignoredInAccounting) {
          continue;
        }
        if (!strings.includes(movement.identifier)) {
          data[i] = { ...data[i], ignoredInAccounting: false };
        }
      }
      commit(HistoryMutations.SET_MOVEMENTS, {
        data,
        found: state.assetMovements.found,
        limit: state.assetMovements.limit
      } as AssetMovements);
    } else if (type === IGNORE_TRANSACTIONS) {
      const data = [...state.transactions.data];

      for (let i = 0; i < data.length; i++) {
        const transaction: Writeable<EthTransactionEntry> = data[i];
        if (!transaction.ignoredInAccounting) {
          continue;
        }
        const key =
          transaction.txHash + transaction.fromAddress + transaction.nonce;
        if (!strings.includes(key)) {
          data[i] = { ...data[i], ignoredInAccounting: false };
        }
      }
      commit(HistoryMutations.SET_TRANSACTIONS, {
        data,
        found: state.transactions.found,
        limit: state.transactions.limit
      } as EthTransactions);
    } else if (type === IGNORE_LEDGER_ACTION) {
      const data = [...state.ledgerActions.data];

      for (let i = 0; i < data.length; i++) {
        const ledgerAction: Writeable<LedgerActionEntry> = data[i];
        if (!ledgerAction.ignoredInAccounting) {
          continue;
        }

        if (!strings.includes(ledgerAction.identifier.toString())) {
          data[i] = { ...data[i], ignoredInAccounting: false };
        }
      }
      commit(HistoryMutations.SET_LEDGER_ACTIONS, {
        data,
        found: state.ledgerActions.found,
        limit: state.ledgerActions.limit
      } as LedgerActions);
    }
    return { success: true };
  },

  async [HistoryActions.REMOVE_EXCHANGE_TRADES](
    { commit, state },
    location: SupportedExchange
  ) {
    const data = state.trades.data;
    const withoutLocation = data.filter(entry => entry.location !== location);
    const trades: HistoricData<TradeEntry> = {
      data: withoutLocation,
      found: state.trades.found - withoutLocation.length,
      limit: state.trades.limit
    };

    commit(HistoryMutations.SET_TRADES, trades);
  },
  async [HistoryActions.REMOVE_EXCHANGE_MOVEMENTS](
    { commit, state: { assetMovements } },
    location: SupportedExchange
  ) {
    const data = assetMovements.data;
    const withoutLocation = data.filter(entry => entry.location !== location);
    const trades: HistoricData<AssetMovementEntry> = {
      data: withoutLocation,
      found: assetMovements.found - withoutLocation.length,
      limit: assetMovements.limit
    };

    commit(HistoryMutations.SET_MOVEMENTS, trades);
  },
  async [HistoryActions.PURGE_TRANSACTIONS]({
    commit,
    rootGetters: { status }
  }) {
    commit(
      HistoryMutations.SET_TRANSACTIONS,
      defaultHistoricState<EthTransactions>()
    );
    setStatus(Status.NONE, Section.TX, status, commit);
  },
  async [HistoryActions.PURGE_EXCHANGE](
    { commit, dispatch },
    exchange: SupportedExchange | typeof ALL_CENTRALIZED_EXCHANGES
  ) {
    if (exchange === ALL_CENTRALIZED_EXCHANGES) {
      commit(HistoryMutations.SET_TRADES, defaultHistoricState());
      commit(HistoryMutations.SET_MOVEMENTS, defaultHistoricState());
    } else {
      await dispatch(HistoryActions.REMOVE_EXCHANGE_TRADES, exchange);
      await dispatch(HistoryActions.REMOVE_EXCHANGE_MOVEMENTS, exchange);
    }
  },
  async [HistoryActions.FETCH_GITCOIN_GRANT](
    { commit },
    payload: GitcoinGrantEventsPayload
  ): Promise<ActionResult<GitcoinGrants>> {
    try {
      const { taskId } = await api.history.gatherGitcoinGrandEvents(payload);

      const meta: TaskMeta = {
        title: i18n
          .t('actions.balances.gitcoin_grant.task.title', {
            grant: 'grantId' in payload ? payload.grantId : ''
          })
          .toString(),
        ignoreResult: false,
        numericKeys: balanceKeys
      };

      const type = TaskType.GITCOIN_GRANT_EVENTS;
      const task = createTask(taskId, type, meta);

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<GitcoinGrants, TaskMeta>(type);

      return { result, message: '' };
    } catch (e) {
      return {
        result: {},
        message: e.message
      };
    }
  }
};
