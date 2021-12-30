import { ActionResult } from '@rotki/common/lib/data';
import {
  GitcoinGrantEventsPayload,
  GitcoinGrants
} from '@rotki/common/lib/gitcoin';
import { ActionContext, ActionTree } from 'vuex';
import { exchangeName } from '@/components/history/consts';
import i18n from '@/i18n';
import { balanceKeys } from '@/services/consts';
import {
  AssetMovement,
  AssetMovementCollectionResponse,
  AssetMovementRequestPayload,
  EntryWithMeta,
  EthTransaction,
  EthTransactionCollectionResponse,
  LedgerAction,
  LedgerActionCollectionResponse,
  LedgerActionRequestPayload,
  NewLedgerAction,
  NewTrade,
  Trade,
  TradeCollectionResponse,
  TradeLocation,
  TradeRequestPayload,
  TransactionRequestPayload
} from '@/services/history/types';
import { api } from '@/services/rotkehlchen-api';
import { ALL_CENTRALIZED_EXCHANGES } from '@/services/session/consts';
import { mapCollectionResponse } from '@/services/utils';
import { Section, Status } from '@/store/const';
import { HistoryActions, HistoryMutations } from '@/store/history/consts';
import {
  AssetMovementEntry,
  EthTransactionEntry,
  HistoryState,
  IgnoreActionPayload,
  LedgerActionEntry,
  TradeEntry
} from '@/store/history/types';
import { mapCollectionEntriesWithMeta } from '@/store/history/utils';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { ActionStatus, Message, RotkehlchenState } from '@/store/types';
import { getStatusUpdater, setStatus } from '@/store/utils';
import { Collection, CollectionResponse } from '@/types/collection';
import { SupportedExchange } from '@/types/exchanges';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';

const ignoreInAccounting = async (
  { commit, state }: ActionContext<HistoryState, RotkehlchenState>,
  { actionIds, type }: IgnoreActionPayload,
  ignore: boolean
) => {
  try {
    const result = ignore
      ? await api.ignoreActions(actionIds, type)
      : await api.unignoreActions(actionIds, type);
    const newState = { ...state.ignored, ...result };
    commit(HistoryMutations.SET_IGNORED, newState);
  } catch (e: any) {
    let title: string;
    let description: string;
    if (ignore) {
      title = i18n.t('actions.ignore.error.title').toString();
    } else {
      title = i18n.t('actions.unignore.error.title').toString();
    }

    if (ignore) {
      description = i18n
        .t('actions.ignore.error.description', { error: e.message })
        .toString();
    } else {
      description = i18n
        .t('actions.unignore.error.description', { error: e.message })
        .toString();
    }
    commit(
      'setMessage',
      {
        success: false,
        title,
        description
      } as Message,
      { root: true }
    );
    return { success: false };
  }

  return { success: true };
};

export const actions: ActionTree<HistoryState, RotkehlchenState> = {
  async [HistoryActions.FETCH_ASSOCIATED_LOCATIONS]({ commit }): Promise<void> {
    const associatedLocations = await api.history.associatedLocations();

    commit(HistoryMutations.SET_ASSOCIATED_LOCATIONS, associatedLocations);
  },

  async [HistoryActions.FETCH_TRADES](
    { commit, rootGetters: { status } },
    {
      payload,
      onlyLocation
    }: {
      payload: Partial<TradeRequestPayload>;
      onlyLocation?: SupportedExchange;
    }
  ): Promise<void> {
    const { awaitTask, isTaskRunning } = useTasks();
    const { setStatus, loading, isFirstLoad } = getStatusUpdater(
      commit,
      Section.TRADES,
      status,
      !!onlyLocation
    );
    const taskType = TaskType.TRADES;

    const fetchTrades: (
      parameters?: Partial<TradeRequestPayload>
    ) => Promise<Collection<TradeEntry>> = async parameters => {
      const defaults = {
        limit: 1,
        offset: 0,
        ascending: false,
        orderByAttribute: 'time'
      };

      const params: TradeRequestPayload = Object.assign(defaults, parameters);

      if (params.onlyCache) {
        const result = await api.history.trades(params);
        return mapCollectionEntriesWithMeta<Trade>(
          mapCollectionResponse(result)
        ) as Collection<TradeEntry>;
      }

      const { taskId } = await api.history.tradesTask(params);
      const location = parameters?.location ?? '';
      const exchange = location
        ? exchangeName(location as TradeLocation)
        : i18n.tc('actions.trades.all_exchanges');
      const taskMeta = {
        title: i18n.tc('actions.trades.task.title'),
        description: i18n.tc('actions.trades.task.description', undefined, {
          exchange
        }),
        location,
        numericKeys: []
      };

      const { result } = await awaitTask<
        CollectionResponse<EntryWithMeta<Trade>>,
        TaskMeta
      >(taskId, taskType, taskMeta, true);

      setStatus(
        isTaskRunning(taskType).value ? Status.REFRESHING : Status.LOADED
      );

      const parsedResult = TradeCollectionResponse.parse(result);
      return mapCollectionEntriesWithMeta<Trade>(
        mapCollectionResponse(parsedResult)
      ) as Collection<TradeEntry>;
    };

    try {
      const firstLoad = isFirstLoad();
      const onlyCache = firstLoad ? false : payload.onlyCache;
      if ((isTaskRunning(taskType).value || loading()) && !onlyCache) {
        return;
      }

      const fetchOnlyCache = async () => {
        const cacheParams = { ...payload, onlyCache: true };
        const data = await fetchTrades(cacheParams);
        commit(HistoryMutations.SET_TRADES, data);
      };

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      if (!onlyLocation) await fetchOnlyCache();

      if (!onlyCache || onlyLocation) {
        setStatus(Status.REFRESHING);
        const { notify } = useNotifications();

        const exchange = onlyLocation
          ? exchangeName(onlyLocation as TradeLocation)
          : i18n.tc('actions.trades.all_exchanges');

        await fetchTrades({ location: onlyLocation, onlyCache: false }).catch(
          error => {
            notify({
              title: i18n.tc('actions.trades.error.title', undefined, {
                exchange
              }),
              message: i18n.tc('actions.trades.error.description', undefined, {
                exchange,
                error
              }),
              display: true
            });
          }
        );

        if (!onlyLocation) await fetchOnlyCache();
      }

      setStatus(
        isTaskRunning(taskType).value ? Status.REFRESHING : Status.LOADED
      );
    } catch (e: any) {
      logger.error(e);
      setStatus(Status.NONE);
    }
  },

  async [HistoryActions.ADD_EXTERNAL_TRADE](
    { dispatch },
    trade: NewTrade
  ): Promise<ActionStatus> {
    let success = false;
    let message = '';
    try {
      await api.history.addExternalTrade(trade);
      success = true;
    } catch (e: any) {
      message = e.message;
    }

    dispatch(HistoryActions.FETCH_ASSOCIATED_LOCATIONS);
    return { success, message };
  },

  async [HistoryActions.EDIT_EXTERNAL_TRADE](
    { dispatch },
    trade: TradeEntry
  ): Promise<ActionStatus> {
    let success = false;
    let message = '';
    try {
      await api.history.editExternalTrade(trade);
      success = true;
    } catch (e: any) {
      message = e.message;
    }

    dispatch(HistoryActions.FETCH_ASSOCIATED_LOCATIONS);
    return { success, message };
  },

  async [HistoryActions.DELETE_EXTERNAL_TRADE](
    { dispatch },
    tradeId: string
  ): Promise<ActionStatus> {
    let success = false;
    let message = '';
    try {
      success = await api.history.deleteExternalTrade(tradeId);
    } catch (e: any) {
      message = e.message;
    }

    dispatch(HistoryActions.FETCH_ASSOCIATED_LOCATIONS);
    return { success, message };
  },

  async [HistoryActions.FETCH_MOVEMENTS](
    { commit, rootGetters: { status } },
    {
      payload,
      onlyLocation
    }: {
      payload: Partial<AssetMovementRequestPayload>;
      onlyLocation?: SupportedExchange;
    }
  ): Promise<void> {
    const { awaitTask, isTaskRunning } = useTasks();
    const { setStatus, loading, isFirstLoad } = getStatusUpdater(
      commit,
      Section.ASSET_MOVEMENT,
      status,
      !!onlyLocation
    );
    const taskType = TaskType.MOVEMENTS;

    const fetchAssetMovements: (
      parameters?: Partial<AssetMovementRequestPayload>
    ) => Promise<Collection<AssetMovementEntry>> = async parameters => {
      const defaults = {
        limit: 1,
        offset: 0,
        ascending: false,
        orderByAttribute: 'time'
      };

      const params: AssetMovementRequestPayload = Object.assign(
        defaults,
        parameters
      );

      if (params.onlyCache) {
        const result = await api.history.assetMovements(params);
        return mapCollectionEntriesWithMeta<AssetMovement>(
          mapCollectionResponse(result)
        ) as Collection<AssetMovementEntry>;
      }

      const { taskId } = await api.history.assetMovementsTask(params);
      const location = parameters?.location ?? '';
      const exchange = location
        ? exchangeName(location as TradeLocation)
        : i18n.tc('actions.asset_movements.all_exchanges');
      const taskMeta = {
        title: i18n.tc('actions.asset_movements.task.title'),
        description: i18n.tc(
          'actions.asset_movements.task.description',
          undefined,
          {
            exchange
          }
        ),
        location,
        numericKeys: []
      };

      const { result } = await awaitTask<
        CollectionResponse<EntryWithMeta<AssetMovement>>,
        TaskMeta
      >(taskId, taskType, taskMeta, true);

      setStatus(
        isTaskRunning(taskType).value ? Status.REFRESHING : Status.LOADED
      );

      const parsedResult = AssetMovementCollectionResponse.parse(result);
      return mapCollectionEntriesWithMeta<AssetMovement>(
        mapCollectionResponse(parsedResult)
      ) as Collection<AssetMovementEntry>;
    };

    try {
      const firstLoad = isFirstLoad();
      const onlyCache = firstLoad ? false : payload.onlyCache;
      if ((isTaskRunning(taskType).value || loading()) && !onlyCache) {
        return;
      }

      const fetchOnlyCache = async () => {
        const cacheParams = { ...payload, onlyCache: true };
        const data = await fetchAssetMovements(cacheParams);
        commit(HistoryMutations.SET_MOVEMENTS, data);
      };

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      if (!onlyLocation) await fetchOnlyCache();

      if (!onlyCache || onlyLocation) {
        setStatus(Status.REFRESHING);
        const { notify } = useNotifications();

        const exchange = onlyLocation
          ? exchangeName(onlyLocation as TradeLocation)
          : i18n.tc('actions.asset_movements.all_exchanges');

        await fetchAssetMovements({
          location: onlyLocation,
          onlyCache: false
        }).catch(error => {
          notify({
            title: i18n.tc('actions.asset_movements.error.title', undefined, {
              exchange
            }),
            message: i18n.tc(
              'actions.asset_movements.error.description',
              undefined,
              {
                exchange,
                error
              }
            ),
            display: true
          });
        });

        if (!onlyLocation) await fetchOnlyCache();
      }

      setStatus(
        isTaskRunning(taskType).value ? Status.REFRESHING : Status.LOADED
      );
    } catch (e: any) {
      logger.error(e);
      setStatus(Status.NONE);
    }
  },

  async [HistoryActions.FETCH_TRANSACTIONS](
    { commit, rootGetters: { 'balances/ethAddresses': ethAddresses, status } },
    payload: Partial<TransactionRequestPayload>
  ): Promise<void> {
    const { awaitTask, isTaskRunning } = useTasks();
    const { setStatus, loading, isFirstLoad } = getStatusUpdater(
      commit,
      Section.TX,
      status
    );
    const taskType = TaskType.TX;

    const fetchTransactions: (
      parameters?: Partial<TransactionRequestPayload>
    ) => Promise<Collection<EthTransactionEntry>> = async parameters => {
      const defaults = {
        limit: 1,
        offset: 0,
        ascending: false,
        orderByAttribute: 'timestamp'
      };

      const params: TransactionRequestPayload = Object.assign(
        defaults,
        parameters
      );

      if (params.onlyCache) {
        const result = await api.history.ethTransactions(params);
        return mapCollectionEntriesWithMeta<EthTransaction>(
          mapCollectionResponse(result)
        ) as Collection<EthTransactionEntry>;
      }

      const { taskId } = await api.history.ethTransactionsTask(params);
      const address = parameters?.address ?? '';
      const taskMeta = {
        title: i18n.t('actions.transactions.task.title').toString(),
        description: address
          ? i18n
              .t('actions.transactions.task.description', {
                address
              })
              .toString()
          : undefined,
        numericKeys: [],
        address
      };

      const { result } = await awaitTask<
        CollectionResponse<EntryWithMeta<EthTransaction>>,
        TaskMeta
      >(taskId, taskType, taskMeta, true);

      setStatus(
        isTaskRunning(taskType).value ? Status.REFRESHING : Status.LOADED
      );

      const parsedResult = EthTransactionCollectionResponse.parse(result);
      return mapCollectionEntriesWithMeta<EthTransaction>(
        mapCollectionResponse(parsedResult)
      ) as Collection<EthTransactionEntry>;
    };

    try {
      const firstLoad = isFirstLoad();
      const onlyCache = firstLoad ? false : payload.onlyCache;
      if ((isTaskRunning(taskType).value || loading()) && !onlyCache) {
        return;
      }

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      const cacheParams = { ...payload, onlyCache: true };
      const data = await fetchTransactions(cacheParams);
      commit(HistoryMutations.SET_TRANSACTIONS, data);

      if (!onlyCache) {
        setStatus(Status.REFRESHING);
        const { notify } = useNotifications();
        const refreshAddressTxs = ethAddresses.map((address: string) =>
          fetchTransactions({ address, onlyCache: false }).catch(error => {
            notify({
              title: i18n.t('actions.transactions.error.title').toString(),
              message: i18n
                .t('actions.transactions.error.description', {
                  error,
                  address
                })
                .toString(),
              display: true
            });
          })
        );
        await Promise.all(refreshAddressTxs);

        const cacheParams = { ...payload, onlyCache: true };
        const data = await fetchTransactions(cacheParams);
        commit(HistoryMutations.SET_TRANSACTIONS, data);
      }

      setStatus(
        isTaskRunning(taskType).value ? Status.REFRESHING : Status.LOADED
      );
    } catch (e: any) {
      logger.error(e);
      setStatus(Status.NONE);
    }
  },

  async [HistoryActions.FETCH_LEDGER_ACTIONS](
    { commit, rootGetters: { status } },
    {
      payload,
      onlyLocation
    }: {
      payload: Partial<LedgerActionRequestPayload>;
      onlyLocation?: SupportedExchange;
    }
  ): Promise<void> {
    const { awaitTask, isTaskRunning } = useTasks();
    const { setStatus, loading, isFirstLoad } = getStatusUpdater(
      commit,
      Section.LEDGER_ACTIONS,
      status,
      !!onlyLocation
    );
    const taskType = TaskType.LEDGER_ACTIONS;

    const fetchLedgerActions: (
      parameters?: Partial<LedgerActionRequestPayload>
    ) => Promise<Collection<LedgerActionEntry>> = async parameters => {
      const defaults = {
        limit: 1,
        offset: 0,
        ascending: false,
        orderByAttribute: 'timestamp'
      };

      const params: LedgerActionRequestPayload = Object.assign(
        defaults,
        parameters
      );

      if (params.onlyCache) {
        const result = await api.history.ledgerActions(params);
        return mapCollectionEntriesWithMeta<LedgerAction>(
          mapCollectionResponse(result)
        ) as Collection<LedgerActionEntry>;
      }

      const { taskId } = await api.history.ledgerActionsTask(params);
      const location = parameters?.location ?? '';
      const exchange = location
        ? exchangeName(location as TradeLocation)
        : i18n.tc('actions.trades.all_exchanges');
      const taskMeta = {
        title: i18n.tc('actions.ledger_actions.task.title'),
        description: i18n.tc(
          'actions.ledger_actions.task.description',
          undefined,
          {
            exchange
          }
        ),
        location,
        numericKeys: []
      };

      const { result } = await awaitTask<
        CollectionResponse<EntryWithMeta<LedgerAction>>,
        TaskMeta
      >(taskId, taskType, taskMeta, true);

      setStatus(
        isTaskRunning(taskType).value ? Status.REFRESHING : Status.LOADED
      );

      const parsedResult = LedgerActionCollectionResponse.parse(result);
      return mapCollectionEntriesWithMeta<LedgerAction>(
        mapCollectionResponse(parsedResult)
      ) as Collection<LedgerActionEntry>;
    };

    try {
      const firstLoad = isFirstLoad();
      const onlyCache = firstLoad ? false : payload.onlyCache;
      if ((isTaskRunning(taskType).value || loading()) && !onlyCache) {
        return;
      }

      const fetchOnlyCache = async () => {
        const cacheParams = { ...payload, onlyCache: true };
        const data = await fetchLedgerActions(cacheParams);
        commit(HistoryMutations.SET_LEDGER_ACTIONS, data);
      };

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      if (!onlyLocation) await fetchOnlyCache();

      if (!onlyCache || onlyLocation) {
        setStatus(Status.REFRESHING);
        const { notify } = useNotifications();

        const exchange = onlyLocation
          ? exchangeName(onlyLocation as TradeLocation)
          : i18n.tc('actions.ledger_actions.all_exchanges');

        await fetchLedgerActions({
          location: onlyLocation,
          onlyCache: false
        }).catch(error => {
          notify({
            title: i18n.tc('actions.ledger_actions.error.title', undefined, {
              exchange
            }),
            message: i18n.tc(
              'actions.ledger_actions.error.description',
              undefined,
              {
                exchange,
                error
              }
            ),
            display: true
          });
        });

        if (!onlyLocation) await fetchOnlyCache();
      }

      setStatus(
        isTaskRunning(taskType).value ? Status.REFRESHING : Status.LOADED
      );
    } catch (e: any) {
      logger.error(e);
      setStatus(Status.NONE);
    }
  },

  async [HistoryActions.ADD_LEDGER_ACTION](
    { dispatch },
    ledgerAction: NewLedgerAction
  ): Promise<ActionStatus> {
    let success = false;
    let message = '';
    try {
      await api.history.addLedgerAction(ledgerAction);
      success = true;
    } catch (e: any) {
      message = e.message;
    }

    dispatch(HistoryActions.FETCH_ASSOCIATED_LOCATIONS);
    return { success, message };
  },

  async [HistoryActions.EDIT_LEDGER_ACTION](
    { dispatch },
    ledgerAction: LedgerAction
  ): Promise<ActionStatus> {
    let success = false;
    let message = '';
    try {
      await api.history.editLedgerAction(ledgerAction);
      success = true;
    } catch (e: any) {
      message = e.message;
    }

    dispatch(HistoryActions.FETCH_ASSOCIATED_LOCATIONS);
    return { success, message };
  },

  async [HistoryActions.DELETE_LEDGER_ACTION](
    { dispatch },
    identifier: number
  ): Promise<ActionStatus> {
    let success = false;
    let message = '';
    try {
      success = await api.history.deleteLedgerAction(identifier);
    } catch (e: any) {
      message = e.message;
    }

    dispatch(HistoryActions.FETCH_ASSOCIATED_LOCATIONS);
    return { success, message };
  },

  async [HistoryActions.IGNORE_ACTIONS](
    context,
    payload: IgnoreActionPayload
  ): Promise<ActionStatus> {
    return ignoreInAccounting(context, payload, true);
  },

  async [HistoryActions.UNIGNORE_ACTION](
    context,
    payload: IgnoreActionPayload
  ) {
    return ignoreInAccounting(context, payload, false);
  },

  async [HistoryActions.PURGE_EXCHANGE](
    { commit, dispatch, rootGetters: { status } },
    exchange: SupportedExchange | typeof ALL_CENTRALIZED_EXCHANGES
  ) {
    function resetStatus(section: Section) {
      setStatus(Status.NONE, section, status, commit);
    }
    if (exchange === ALL_CENTRALIZED_EXCHANGES) {
      resetStatus(Section.TRADES);
      resetStatus(Section.ASSET_MOVEMENT);
      resetStatus(Section.LEDGER_ACTIONS);
    } else {
      dispatch(HistoryActions.PURGE_HISTORY_LOCATION, exchange);
    }
  },

  async [HistoryActions.PURGE_HISTORY_LOCATION](
    { dispatch },
    exchange: SupportedExchange
  ) {
    dispatch(HistoryActions.FETCH_TRADES, {
      payload: { onlyCache: false },
      onlyLocation: exchange
    });

    dispatch(HistoryActions.FETCH_MOVEMENTS, {
      payload: { onlyCache: false },
      onlyLocation: exchange
    });

    dispatch(HistoryActions.FETCH_LEDGER_ACTIONS, {
      payload: { onlyCache: false },
      onlyLocation: exchange
    });
  },

  async [HistoryActions.FETCH_GITCOIN_GRANT](
    _,
    payload: GitcoinGrantEventsPayload
  ): Promise<ActionResult<GitcoinGrants>> {
    try {
      const { awaitTask } = useTasks();
      const { taskId } = await api.history.gatherGitcoinGrandEvents(payload);
      const meta: TaskMeta = {
        title: i18n
          .t('actions.balances.gitcoin_grant.task.title', {
            grant: 'grantId' in payload ? payload.grantId : ''
          })
          .toString(),
        numericKeys: balanceKeys
      };
      const { result } = await awaitTask<GitcoinGrants, TaskMeta>(
        taskId,
        TaskType.GITCOIN_GRANT_EVENTS,
        meta
      );
      return { result, message: '' };
    } catch (e: any) {
      return {
        result: {},
        message: e.message
      };
    }
  },
  async [HistoryActions.FETCH_IGNORED]({ commit }) {
    const notify = (error?: any) => {
      logger.error(error);
      const message = error?.message ?? error ?? '';
      const { notify } = useNotifications();
      notify({
        title: i18n.t('actions.history.fetch_ignored.error.title').toString(),
        message: i18n
          .t('actions.history.fetch_ignored.error.message', { message })
          .toString(),
        display: true
      });
    };
    try {
      const result = await api.history.fetchIgnored();
      commit(HistoryMutations.SET_IGNORED, result);
    } catch (e: any) {
      notify(e);
    }
  }
};
