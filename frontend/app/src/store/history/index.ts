import { ActionResult } from '@rotki/common/lib/data';
import {
  GitcoinGrantEventsPayload,
  GitcoinGrants
} from '@rotki/common/lib/gitcoin';
import { computed, Ref, ref } from '@vue/composition-api';
import isEqual from 'lodash/isEqual';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { exchangeName } from '@/components/history/consts';
import i18n from '@/i18n';
import { balanceKeys } from '@/services/consts';
import { IgnoredActions } from '@/services/history/const';
import {
  AssetMovement,
  AssetMovementCollectionResponse,
  AssetMovementRequestPayload,
  EntryWithMeta,
  EthTransaction,
  EthTransactionCollectionResponse,
  HistoryRequestPayload,
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
import {
  AssetMovementEntry,
  EthTransactionEntry,
  IgnoreActionPayload,
  LedgerActionEntry,
  TradeEntry
} from '@/store/history/types';
import { mapCollectionEntriesWithMeta } from '@/store/history/utils';
import { useNotifications } from '@/store/notifications';
import store, { useMainStore } from '@/store/store';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { getStatusUpdater, setStatus } from '@/store/utils';
import { Collection, CollectionResponse } from '@/types/collection';
import { SupportedExchange } from '@/types/exchanges';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';

const defaultHistoricState = <T>(): Collection<T> => ({
  found: 0,
  limit: 0,
  data: [],
  total: 0
});

const defaultHistoricPayloadState = (
  timestampKey: string = 'time'
): HistoryRequestPayload => {
  const itemsPerPage = store.state.settings!.itemsPerPage;

  return {
    limit: itemsPerPage,
    offset: 0,
    orderByAttribute: timestampKey,
    ascending: false
  };
};

export const useHistory = defineStore('history', () => {
  // associated locations
  const associatedLocations = ref<TradeLocation[]>([]);

  const fetchAssociatedLocations = async () => {
    associatedLocations.value = await api.history.associatedLocations();
  };

  // Ignored
  const ignored = ref<IgnoredActions>({});

  const fetchIgnored = async () => {
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
      ignored.value = await api.history.fetchIgnored();
    } catch (e: any) {
      notify(e);
    }
  };

  const { setMessage } = useMainStore();

  const ignoreInAccounting = async (
    { actionIds, type }: IgnoreActionPayload,
    ignore: boolean
  ) => {
    try {
      ignore
        ? await api.ignoreActions(actionIds, type)
        : await api.unignoreActions(actionIds, type);
      await fetchIgnored();
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
      setMessage({
        success: false,
        title,
        description
      });
      return { success: false };
    }

    return { success: true };
  };

  // Purge
  const purgeHistoryLocation = async (exchange: SupportedExchange) => {
    useTrades().fetchTrades(true, exchange).then();
    useAssetMovements().fetchAssetMovements(true, exchange).then();
    useLedgerActions().fetchLedgerActions(true, exchange).then();
  };

  const purgeExchange = async (
    exchange: SupportedExchange | typeof ALL_CENTRALIZED_EXCHANGES
  ) => {
    function resetStatus(section: Section) {
      setStatus(Status.NONE, section);
    }
    if (exchange === ALL_CENTRALIZED_EXCHANGES) {
      resetStatus(Section.TRADES);
      resetStatus(Section.ASSET_MOVEMENT);
      resetStatus(Section.LEDGER_ACTIONS);
    } else {
      await purgeHistoryLocation(exchange);
    }
  };

  // Gitcoin
  const fetchGitcoinGrant = async (
    payload: GitcoinGrantEventsPayload
  ): Promise<ActionResult<GitcoinGrants>> => {
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
  };

  // Reset
  const reset = () => {
    associatedLocations.value = [];
    ignored.value = {};
    useTrades().reset();
    useAssetMovements().reset();
    useTransactions().reset();
    useLedgerActions().reset();
  };

  return {
    associatedLocations,
    fetchAssociatedLocations,
    ignored,
    fetchIgnored,
    ignoreInAccounting,
    purgeExchange,
    purgeHistoryLocation,
    fetchGitcoinGrant,
    reset
  };
});

export const useTrades = defineStore('history/trades', () => {
  const { fetchAssociatedLocations } = useHistory();

  const trades = ref(defaultHistoricState<TradeEntry>()) as Ref<
    Collection<TradeEntry>
  >;

  const tradesPayload = ref<Partial<TradeRequestPayload>>(
    defaultHistoricPayloadState()
  );

  const fetchTrades = async (
    refresh: boolean = false,
    onlyLocation?: SupportedExchange
  ) => {
    const { awaitTask, isTaskRunning } = useTasks();
    const { setStatus, loading, isFirstLoad } = getStatusUpdater(
      Section.TRADES,
      !!onlyLocation
    );
    const taskType = TaskType.TRADES;

    const fetchTradesHandler = async (
      onlyCache: boolean,
      parameters?: Partial<TradeRequestPayload>
    ) => {
      const defaults: TradeRequestPayload = {
        limit: 1,
        offset: 0,
        ascending: false,
        orderByAttribute: 'time',
        onlyCache
      };

      const payload: TradeRequestPayload = Object.assign(
        defaults,
        parameters ?? tradesPayload.value
      );

      if (onlyCache) {
        const result = await api.history.trades(payload);
        return mapCollectionEntriesWithMeta<Trade>(
          mapCollectionResponse(result)
        ) as Collection<TradeEntry>;
      }

      const { taskId } = await api.history.tradesTask(payload);
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
      const onlyCache = firstLoad ? false : !refresh;
      if ((isTaskRunning(taskType).value || loading()) && !onlyCache) {
        return;
      }

      if (firstLoad || refresh) {
        fetchAssociatedLocations().then();
      }

      const fetchOnlyCache = async () => {
        trades.value = await fetchTradesHandler(true);
      };

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      if (!onlyLocation) await fetchOnlyCache();

      if (!onlyCache || onlyLocation) {
        setStatus(Status.REFRESHING);
        const { notify } = useNotifications();

        const exchange = onlyLocation
          ? exchangeName(onlyLocation as TradeLocation)
          : i18n.tc('actions.trades.all_exchanges');

        await fetchTradesHandler(false, { location: onlyLocation }).catch(
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
    } catch (e) {
      logger.error(e);
      setStatus(Status.NONE);
    }
  };

  const updateTradesPayload = (newPayload: Partial<TradeRequestPayload>) => {
    if (!isEqual(tradesPayload.value, newPayload)) {
      tradesPayload.value = newPayload;
      fetchTrades().then();
    }
  };

  const addExternalTrade = async (trade: NewTrade): Promise<ActionStatus> => {
    let success = false;
    let message = '';
    try {
      await api.history.addExternalTrade(trade);
      success = true;
    } catch (e: any) {
      message = e.message;
    }

    await Promise.all([fetchAssociatedLocations(), fetchTrades()]);

    return { success, message };
  };

  const editExternalTrade = async (
    trade: TradeEntry
  ): Promise<ActionStatus> => {
    let success = false;
    let message = '';
    try {
      await api.history.editExternalTrade(trade);
      success = true;
    } catch (e: any) {
      message = e.message;
    }

    await Promise.all([fetchAssociatedLocations(), fetchTrades()]);
    return { success, message };
  };

  const deleteExternalTrade = async (
    tradeId: string
  ): Promise<ActionStatus> => {
    let success = false;
    let message = '';
    try {
      success = await api.history.deleteExternalTrade(tradeId);
    } catch (e: any) {
      message = e.message;
    }

    await Promise.all([fetchAssociatedLocations(), fetchTrades()]);
    return { success, message };
  };

  const reset = () => {
    trades.value = defaultHistoricState<TradeEntry>();
  };

  return {
    trades,
    tradesPayload,
    updateTradesPayload,
    fetchTrades,
    addExternalTrade,
    editExternalTrade,
    deleteExternalTrade,
    reset
  };
});

export const useAssetMovements = defineStore('history/assetMovements', () => {
  const { fetchAssociatedLocations } = useHistory();

  const assetMovements = ref(defaultHistoricState<AssetMovementEntry>()) as Ref<
    Collection<AssetMovementEntry>
  >;

  const assetMovementsPayload = ref<Partial<AssetMovementRequestPayload>>(
    defaultHistoricPayloadState()
  );

  const fetchAssetMovements = async (
    refresh: boolean = false,
    onlyLocation?: SupportedExchange
  ) => {
    const { awaitTask, isTaskRunning } = useTasks();
    const { setStatus, loading, isFirstLoad } = getStatusUpdater(
      Section.ASSET_MOVEMENT,
      !!onlyLocation
    );
    const taskType = TaskType.MOVEMENTS;

    const fetchAssetMovementsHandler = async (
      onlyCache: boolean,
      parameters?: Partial<AssetMovementRequestPayload>
    ) => {
      const defaults: AssetMovementRequestPayload = {
        limit: 1,
        offset: 0,
        ascending: false,
        orderByAttribute: 'time',
        onlyCache
      };

      const payload: AssetMovementRequestPayload = Object.assign(
        defaults,
        parameters ?? assetMovementsPayload.value
      );

      if (onlyCache) {
        const result = await api.history.assetMovements(payload);
        return mapCollectionEntriesWithMeta<AssetMovement>(
          mapCollectionResponse(result)
        ) as Collection<AssetMovementEntry>;
      }

      const { taskId } = await api.history.assetMovementsTask(payload);
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
      const onlyCache = firstLoad ? false : !refresh;
      if ((isTaskRunning(taskType).value || loading()) && !onlyCache) {
        return;
      }

      if (firstLoad || refresh) {
        fetchAssociatedLocations().then();
      }

      const fetchOnlyCache = async () => {
        assetMovements.value = await fetchAssetMovementsHandler(true);
      };

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      if (!onlyLocation) await fetchOnlyCache();

      if (!onlyCache || onlyLocation) {
        setStatus(Status.REFRESHING);
        const { notify } = useNotifications();

        const exchange = onlyLocation
          ? exchangeName(onlyLocation as TradeLocation)
          : i18n.tc('actions.asset_movements.all_exchanges');

        await fetchAssetMovementsHandler(false, {
          location: onlyLocation
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
    } catch (e) {
      logger.error(e);
      setStatus(Status.NONE);
    }
  };

  const updateAssetMovementsPayload = (
    newPayload: Partial<AssetMovementRequestPayload>
  ) => {
    if (!isEqual(assetMovementsPayload.value, newPayload)) {
      assetMovementsPayload.value = newPayload;
      fetchAssetMovements().then();
    }
  };

  const reset = () => {
    assetMovements.value = defaultHistoricState<AssetMovementEntry>();
  };

  return {
    assetMovements,
    assetMovementsPayload,
    updateAssetMovementsPayload,
    fetchAssetMovements,
    reset
  };
});

export const useTransactions = defineStore('history/transactions', () => {
  // ETH Transactions
  const transactions = ref(defaultHistoricState<EthTransactionEntry>()) as Ref<
    Collection<EthTransactionEntry>
  >;

  const transactionsPayload = ref<Partial<TransactionRequestPayload>>(
    defaultHistoricPayloadState('timestamp')
  );

  const fetchTransactions = async (refresh: boolean = false) => {
    const ethAddresses = computed<string[]>(() => {
      return store.getters['balances/ethAddresses'];
    });

    const { awaitTask, isTaskRunning } = useTasks();
    const { setStatus, loading, isFirstLoad } = getStatusUpdater(Section.TX);
    const taskType = TaskType.TX;

    const fetchTransactionsHandler = async (
      onlyCache: boolean,
      parameters?: Partial<TransactionRequestPayload>
    ) => {
      const defaults: TradeRequestPayload = {
        limit: 1,
        offset: 0,
        ascending: false,
        orderByAttribute: 'timestamp',
        onlyCache
      };

      const payload: TransactionRequestPayload = Object.assign(
        defaults,
        parameters ?? transactionsPayload.value
      );

      if (onlyCache) {
        const result = await api.history.ethTransactions(payload);
        return mapCollectionEntriesWithMeta<EthTransaction>(
          mapCollectionResponse(result)
        ) as Collection<EthTransactionEntry>;
      }

      const { taskId } = await api.history.ethTransactionsTask(payload);
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
      const onlyCache = firstLoad ? false : !refresh;
      if ((isTaskRunning(taskType).value || loading()) && !onlyCache) {
        return;
      }

      const fetchOnlyCache = async () => {
        transactions.value = await fetchTransactionsHandler(true);
      };

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      await fetchOnlyCache();

      if (!onlyCache) {
        setStatus(Status.REFRESHING);
        const { notify } = useNotifications();
        const refreshAddressTxs = ethAddresses.value.map((address: string) =>
          fetchTransactionsHandler(false).catch(error => {
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

        await fetchOnlyCache();
      }

      setStatus(
        isTaskRunning(taskType).value ? Status.REFRESHING : Status.LOADED
      );
    } catch (e) {
      logger.error(e);
      setStatus(Status.NONE);
    }
  };

  const updateTransactionsPayload = (
    newPayload: Partial<TransactionRequestPayload>
  ) => {
    if (!isEqual(transactionsPayload.value, newPayload)) {
      transactionsPayload.value = newPayload;
      fetchTransactions().then();
    }
  };

  const reset = () => {
    transactions.value = defaultHistoricState<EthTransactionEntry>();
  };

  return {
    transactions,
    transactionsPayload,
    updateTransactionsPayload,
    fetchTransactions,
    reset
  };
});

export const useLedgerActions = defineStore('history/ledgerActions', () => {
  const { fetchAssociatedLocations } = useHistory();

  const ledgerActions = ref(defaultHistoricState<LedgerActionEntry>()) as Ref<
    Collection<LedgerActionEntry>
  >;

  const ledgerActionsPayload = ref<Partial<LedgerActionRequestPayload>>(
    defaultHistoricPayloadState('timestamp')
  );

  const fetchLedgerActions = async (
    refresh: boolean = false,
    onlyLocation?: SupportedExchange
  ) => {
    const { awaitTask, isTaskRunning } = useTasks();
    const { setStatus, loading, isFirstLoad } = getStatusUpdater(
      Section.LEDGER_ACTIONS,
      !!onlyLocation
    );
    const taskType = TaskType.LEDGER_ACTIONS;

    const fetchLedgerActionsHandler = async (
      onlyCache: boolean,
      parameters?: Partial<LedgerActionRequestPayload>
    ) => {
      const defaults: LedgerActionRequestPayload = {
        limit: 1,
        offset: 0,
        ascending: false,
        orderByAttribute: 'timestamp',
        onlyCache
      };

      const payload: LedgerActionRequestPayload = Object.assign(
        defaults,
        parameters ?? ledgerActionsPayload.value
      );

      if (onlyCache) {
        const result = await api.history.ledgerActions(payload);
        return mapCollectionEntriesWithMeta<LedgerAction>(
          mapCollectionResponse(result)
        ) as Collection<LedgerActionEntry>;
      }

      const { taskId } = await api.history.ledgerActionsTask(payload);
      const location = parameters?.location ?? '';
      const exchange = location
        ? exchangeName(location as TradeLocation)
        : i18n.tc('actions.ledger_actions.all_exchanges');
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
      const onlyCache = firstLoad ? false : !refresh;
      if ((isTaskRunning(taskType).value || loading()) && !onlyCache) {
        return;
      }

      if (firstLoad || refresh) {
        fetchAssociatedLocations().then();
      }

      const fetchOnlyCache = async () => {
        ledgerActions.value = await fetchLedgerActionsHandler(true);
      };

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      if (!onlyLocation) await fetchOnlyCache();

      if (!onlyCache || onlyLocation) {
        setStatus(Status.REFRESHING);
        const { notify } = useNotifications();

        const exchange = onlyLocation
          ? exchangeName(onlyLocation as TradeLocation)
          : i18n.tc('actions.ledger_actions.all_exchanges');

        await fetchLedgerActionsHandler(false, {
          location: onlyLocation
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
    } catch (e) {
      logger.error(e);
      setStatus(Status.NONE);
    }
  };

  const updateLedgerActionsPayload = (
    newPayload: Partial<LedgerActionRequestPayload>
  ) => {
    if (!isEqual(ledgerActionsPayload.value, newPayload)) {
      ledgerActionsPayload.value = newPayload;
      fetchLedgerActions().then();
    }
  };

  const addLedgerAction = async (
    ledgerAction: NewLedgerAction
  ): Promise<ActionStatus> => {
    let success = false;
    let message = '';
    try {
      await api.history.addLedgerAction(ledgerAction);
      success = true;
    } catch (e: any) {
      message = e.message;
    }

    await Promise.all([fetchAssociatedLocations(), fetchLedgerActions()]);
    return { success, message };
  };

  const editLedgerAction = async (
    ledgerAction: LedgerActionEntry
  ): Promise<ActionStatus> => {
    let success = false;
    let message = '';
    try {
      await api.history.editLedgerAction(ledgerAction);
      success = true;
    } catch (e: any) {
      message = e.message;
    }

    await Promise.all([fetchAssociatedLocations(), fetchLedgerActions()]);
    return { success, message };
  };

  const deleteLedgerAction = async (
    identifier: number
  ): Promise<ActionStatus> => {
    let success = false;
    let message = '';
    try {
      success = await api.history.deleteLedgerAction(identifier);
    } catch (e: any) {
      message = e.message;
    }

    await Promise.all([fetchAssociatedLocations(), fetchLedgerActions()]);
    return { success, message };
  };

  const reset = () => {
    ledgerActions.value = defaultHistoricState<LedgerActionEntry>();
  };

  return {
    ledgerActions,
    ledgerActionsPayload,
    updateLedgerActionsPayload,
    fetchLedgerActions,
    addLedgerAction,
    editLedgerAction,
    deleteLedgerAction,
    reset
  };
});

if (module.hot) {
  module.hot.accept(acceptHMRUpdate(useHistory, module.hot));
  module.hot.accept(acceptHMRUpdate(useTrades, module.hot));
  module.hot.accept(acceptHMRUpdate(useTransactions, module.hot));
  module.hot.accept(acceptHMRUpdate(useLedgerActions, module.hot));
  module.hot.accept(acceptHMRUpdate(useAssetMovements, module.hot));
}
