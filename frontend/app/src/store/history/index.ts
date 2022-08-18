import { Ref, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import isEqual from 'lodash/isEqual';
import { acceptHMRUpdate, defineStore, storeToRefs } from 'pinia';
import { exchangeName } from '@/components/history/consts';
import i18n from '@/i18n';
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
  NewEthTransactionEvent,
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
import { useBlockchainAccountsStore } from '@/store/balances/blockchain-accounts';
import { useEthNamesStore } from '@/store/balances/ethereum-names';
import { Section, Status } from '@/store/const';
import {
  AssetMovementEntry,
  EthTransactionEntry,
  IgnoreActionPayload,
  LedgerActionEntry,
  TradeEntry
} from '@/store/history/types';
import {
  filterAddressesFromWords,
  mapCollectionEntriesWithMeta
} from '@/store/history/utils';
import { useMainStore } from '@/store/main';
import { useNotifications } from '@/store/notifications';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { getStatusUpdater } from '@/store/utils';
import { Collection, CollectionResponse } from '@/types/collection';
import { SupportedExchange } from '@/types/exchanges';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import {
  defaultCollectionState,
  mapCollectionResponse
} from '@/utils/collection';
import { logger } from '@/utils/logging';

const defaultHistoricPayloadState = <
  T extends Object
>(): HistoryRequestPayload<T> => {
  const store = useFrontendSettingsStore();

  return {
    limit: store.itemsPerPage,
    offset: 0,
    orderByAttributes: ['timestamp' as keyof T],
    ascending: [false]
  };
};

export const useHistory = defineStore('history', () => {
  // associated locations
  const associatedLocations = ref<TradeLocation[]>([]);
  const { notify } = useNotifications();

  const fetchAssociatedLocations = async () => {
    const notifyError = (error?: any) => {
      logger.error(error);
      const message = error?.message ?? error ?? '';
      notify({
        title: i18n
          .t('actions.history.fetch_associated_locations.error.title')
          .toString(),
        message: i18n
          .t('actions.history.fetch_associated_locations.error.message', {
            message
          })
          .toString(),
        display: true
      });
    };

    try {
      set(associatedLocations, await api.history.associatedLocations());
    } catch (e: any) {
      notifyError(e);
    }
  };

  // Ignored
  const ignored = ref<IgnoredActions>({});

  const fetchIgnored = async () => {
    const notifyError = (error?: any) => {
      logger.error(error);
      const message = error?.message ?? error ?? '';
      notify({
        title: i18n.t('actions.history.fetch_ignored.error.title').toString(),
        message: i18n
          .t('actions.history.fetch_ignored.error.message', { message })
          .toString(),
        display: true
      });
    };
    try {
      set(ignored, await api.history.fetchIgnored());
    } catch (e: any) {
      notifyError(e);
    }
  };

  const { setMessage } = useMainStore();

  const ignoreInAccounting = async (
    { actionIds, type }: IgnoreActionPayload,
    ignore: boolean
  ): Promise<ActionStatus> => {
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
      return { success: false, message: 'failed' };
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
    const { resetStatus } = getStatusUpdater(Section.TRADES);

    if (exchange === ALL_CENTRALIZED_EXCHANGES) {
      resetStatus();
      resetStatus(Section.ASSET_MOVEMENT);
      resetStatus(Section.LEDGER_ACTIONS);
    } else {
      await purgeHistoryLocation(exchange);
    }
  };

  // Reset
  const reset = () => {
    set(associatedLocations, []);
    set(ignored, {});
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
    reset
  };
});

export const useTrades = defineStore('history/trades', () => {
  const history = useHistory();
  const { associatedLocations } = storeToRefs(history);
  const { fetchAssociatedLocations } = history;

  const trades = ref(defaultCollectionState<TradeEntry>()) as Ref<
    Collection<TradeEntry>
  >;

  const tradesPayload = ref<Partial<TradeRequestPayload>>(
    defaultHistoricPayloadState<Trade>()
  );

  const fetchTrades = async (
    refresh: boolean = false,
    onlyLocation?: SupportedExchange
  ) => {
    const { awaitTask, isTaskRunning } = useTasks();
    const { setStatus, loading, isFirstLoad, resetStatus } = getStatusUpdater(
      Section.TRADES,
      !!onlyLocation
    );
    const taskType = TaskType.TRADES;

    const fetchTradesHandler = async (
      onlyCache: boolean,
      parameters?: Partial<TradeRequestPayload>
    ) => {
      const defaults: TradeRequestPayload = {
        limit: 0,
        offset: 0,
        ascending: [false],
        orderByAttributes: ['timestamp'],
        onlyCache
      };

      const payload: TradeRequestPayload = Object.assign(
        defaults,
        parameters ?? get(tradesPayload)
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
        get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
      );

      const parsedResult = TradeCollectionResponse.parse(result);
      return mapCollectionEntriesWithMeta<Trade>(
        mapCollectionResponse(parsedResult)
      ) as Collection<TradeEntry>;
    };

    try {
      const firstLoad = isFirstLoad();
      const onlyCache = firstLoad ? false : !refresh;
      if ((get(isTaskRunning(taskType)) || loading()) && !onlyCache) {
        return;
      }

      if (firstLoad || refresh) {
        await fetchAssociatedLocations();
      }

      const fetchOnlyCache = async () => {
        set(trades, await fetchTradesHandler(true));
      };

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      if (!onlyLocation) await fetchOnlyCache();

      if (!onlyCache || onlyLocation) {
        setStatus(Status.REFRESHING);
        const { notify } = useNotifications();

        const locations = onlyLocation
          ? [onlyLocation]
          : get(associatedLocations);

        await Promise.all(
          locations.map(async location => {
            const exchange = exchangeName(location as TradeLocation);
            await fetchTradesHandler(false, { location }).catch(error => {
              notify({
                title: i18n.tc('actions.trades.error.title', undefined, {
                  exchange
                }),
                message: i18n.tc(
                  'actions.trades.error.description',
                  undefined,
                  {
                    exchange,
                    error
                  }
                ),
                display: true
              });
            });
          })
        );

        if (!onlyLocation) await fetchOnlyCache();
      }

      setStatus(
        get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
      );
    } catch (e) {
      logger.error(e);
      resetStatus();
    }
  };

  const updateTradesPayload = (newPayload: Partial<TradeRequestPayload>) => {
    if (!isEqual(get(tradesPayload), newPayload)) {
      set(tradesPayload, newPayload);
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
    set(trades, defaultCollectionState<TradeEntry>());
    set(tradesPayload, defaultHistoricPayloadState<Trade>());
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
  const history = useHistory();
  const { associatedLocations } = storeToRefs(history);
  const { fetchAssociatedLocations } = history;

  const assetMovements = ref(
    defaultCollectionState<AssetMovementEntry>()
  ) as Ref<Collection<AssetMovementEntry>>;

  const assetMovementsPayload = ref<Partial<AssetMovementRequestPayload>>(
    defaultHistoricPayloadState<AssetMovement>()
  );

  const fetchAssetMovements = async (
    refresh: boolean = false,
    onlyLocation?: SupportedExchange
  ) => {
    const { awaitTask, isTaskRunning } = useTasks();
    const { setStatus, loading, isFirstLoad, resetStatus } = getStatusUpdater(
      Section.ASSET_MOVEMENT,
      !!onlyLocation
    );
    const taskType = TaskType.MOVEMENTS;

    const fetchAssetMovementsHandler = async (
      onlyCache: boolean,
      parameters?: Partial<AssetMovementRequestPayload>
    ) => {
      const defaults: AssetMovementRequestPayload = {
        limit: 0,
        offset: 0,
        ascending: [false],
        orderByAttributes: ['timestamp'],
        onlyCache
      };

      const payload: AssetMovementRequestPayload = Object.assign(
        defaults,
        parameters ?? get(assetMovementsPayload)
      );

      const { fetchEnsNames } = useEthNamesStore();
      if (onlyCache) {
        const result = await api.history.assetMovements(payload);
        const mapped = mapCollectionEntriesWithMeta<AssetMovement>(
          mapCollectionResponse(result)
        ) as Collection<AssetMovementEntry>;

        const addresses: string[] = [];
        result.entries.forEach(item => {
          if (item.entry.address) {
            addresses.push(item.entry.address);
          }
        });

        fetchEnsNames(addresses, false);

        return mapped;
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
        get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
      );

      const parsedResult = AssetMovementCollectionResponse.parse(result);
      const mapped = mapCollectionEntriesWithMeta<AssetMovement>(
        mapCollectionResponse(parsedResult)
      ) as Collection<AssetMovementEntry>;

      const addresses: string[] = [];
      result.entries.forEach(item => {
        if (item.entry.address) {
          addresses.push(item.entry.address);
        }
      });

      fetchEnsNames(addresses, false);

      return mapped;
    };

    try {
      const firstLoad = isFirstLoad();
      const onlyCache = firstLoad ? false : !refresh;
      if ((get(isTaskRunning(taskType)) || loading()) && !onlyCache) {
        return;
      }

      if (firstLoad || refresh) {
        await fetchAssociatedLocations();
      }

      const fetchOnlyCache = async () => {
        set(assetMovements, await fetchAssetMovementsHandler(true));
      };

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      if (!onlyLocation) await fetchOnlyCache();

      if (!onlyCache || onlyLocation) {
        setStatus(Status.REFRESHING);
        const { notify } = useNotifications();

        const locations = onlyLocation
          ? [onlyLocation]
          : get(associatedLocations);

        await Promise.all(
          locations.map(async location => {
            const exchange = exchangeName(location as TradeLocation);
            await fetchAssetMovementsHandler(false, {
              location
            }).catch(error => {
              notify({
                title: i18n.tc(
                  'actions.asset_movements.error.title',
                  undefined,
                  {
                    exchange
                  }
                ),
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
          })
        );

        if (!onlyLocation) await fetchOnlyCache();
      }

      setStatus(
        get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
      );
    } catch (e) {
      logger.error(e);
      resetStatus();
    }
  };

  const updateAssetMovementsPayload = (
    newPayload: Partial<AssetMovementRequestPayload>
  ) => {
    if (!isEqual(get(assetMovementsPayload), newPayload)) {
      set(assetMovementsPayload, newPayload);
      fetchAssetMovements().then();
    }
  };

  const reset = () => {
    set(assetMovements, defaultCollectionState<AssetMovementEntry>());
    set(assetMovementsPayload, defaultHistoricPayloadState<AssetMovement>());
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
  const transactions = ref(
    defaultCollectionState<EthTransactionEntry>()
  ) as Ref<Collection<EthTransactionEntry>>;

  const fetchedTxHashesEvents = ref<{ [txHash: string]: boolean } | null>({});

  const transactionsPayload = ref<Partial<TransactionRequestPayload>>(
    defaultHistoricPayloadState<EthTransaction>()
  );

  const counterparties = ref<string[]>([]);

  const { ethAddresses } = storeToRefs(useBlockchainAccountsStore());
  const fetchTransactions = async (refresh: boolean = false) => {
    const { awaitTask, isTaskRunning } = useTasks();
    const { setStatus, loading, isFirstLoad, resetStatus } = getStatusUpdater(
      Section.TX
    );
    const taskType = TaskType.TX;

    const fetchTransactionsHandler = async (
      onlyCache: boolean,
      parameters?: Partial<TransactionRequestPayload>
    ) => {
      const defaults: TradeRequestPayload = {
        limit: 0,
        offset: 0,
        ascending: [false],
        orderByAttributes: ['timestamp'],
        onlyCache
      };

      const payload: TransactionRequestPayload = Object.assign(
        defaults,
        parameters ?? get(transactionsPayload)
      );

      const { fetchEnsNames } = useEthNamesStore();
      if (onlyCache) {
        const result = await api.history.ethTransactions(payload);

        const mapped = mapCollectionEntriesWithMeta<EthTransaction>(
          mapCollectionResponse(result)
        ) as Collection<EthTransactionEntry>;

        const addresses = getNotesAddresses(mapped.data);
        fetchEnsNames(addresses, false);

        return mapped;
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
        get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
      );

      const parsedResult = EthTransactionCollectionResponse.parse(result);
      return mapCollectionEntriesWithMeta<EthTransaction>(
        mapCollectionResponse(parsedResult)
      ) as Collection<EthTransactionEntry>;
    };

    try {
      const firstLoad = isFirstLoad();
      const onlyCache = firstLoad ? false : !refresh;
      if ((get(isTaskRunning(taskType)) || loading()) && !onlyCache) {
        return;
      }

      const fetchOnlyCache = async () => {
        set(transactions, await fetchTransactionsHandler(true));
      };

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      await fetchOnlyCache();

      if (!onlyCache) {
        setStatus(Status.REFRESHING);
        const { notify } = useNotifications();
        const refreshAddressTxs = get(ethAddresses).map((address: string) =>
          fetchTransactionsHandler(false, {
            address
          }).catch(error => {
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
        get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
      );
    } catch (e) {
      logger.error(e);
      resetStatus();
    }
  };

  const updateTransactionsPayload = (
    newPayload: Partial<TransactionRequestPayload>
  ) => {
    if (!isEqual(get(transactionsPayload), newPayload)) {
      set(transactionsPayload, newPayload);
      fetchTransactions().then();
    }
  };

  const addTransactionEvent = async (
    event: NewEthTransactionEvent
  ): Promise<ActionStatus> => {
    let success = false;
    let message = '';
    try {
      await api.history.addTransactionEvent(event);
      success = true;
    } catch (e: any) {
      message = e.message;
    }

    await fetchTransactions();

    return { success, message };
  };

  const editTransactionEvent = async (
    event: NewEthTransactionEvent
  ): Promise<ActionStatus> => {
    let success = false;
    let message = '';
    try {
      await api.history.editTransactionEvent(event);
      success = true;
    } catch (e: any) {
      message = e.message;
    }

    await fetchTransactions();
    return { success, message };
  };

  const deleteTransactionEvent = async (
    eventId: number
  ): Promise<ActionStatus> => {
    let success = false;
    let message = '';
    try {
      success = await api.history.deleteTransactionEvent([eventId]);
    } catch (e: any) {
      message = e.message;
    }

    await fetchTransactions();
    return { success, message };
  };

  const checkFetchedTxHashesEvents = (txHashes: string[] | null): string[] => {
    const fetched = get(fetchedTxHashesEvents);
    if (fetched === null) return [];
    if (txHashes === null) {
      set(fetchedTxHashesEvents, null);
      return [];
    }

    const txHashesToFetch = txHashes.filter((txHash: string) => {
      return !fetched[txHash];
    });

    if (txHashesToFetch.length > 0) {
      const txHashesToFetchObj: { [txHash: string]: boolean } = {};
      txHashesToFetch.forEach((txHash: string) => {
        txHashesToFetchObj[txHash] = true;
      });

      set(fetchedTxHashesEvents, {
        ...fetched,
        ...txHashesToFetchObj
      });
    }

    return txHashesToFetch;
  };

  const fetchTransactionEvents = async (
    txHashes: string[] | null,
    ignoreCache: boolean = false
  ) => {
    const isFetchAll = txHashes === null;

    const checked = checkFetchedTxHashesEvents(txHashes);
    const txHashesToFetch = ignoreCache ? txHashes || null : checked;

    if (!isFetchAll && txHashesToFetch && txHashesToFetch.length === 0) return;

    const { awaitTask } = useTasks();

    const taskType = TaskType.TX_EVENTS;
    const { taskId } = await api.history.fetchEthTransactionEvents({
      txHashes: txHashesToFetch,
      ignoreCache
    });
    const taskMeta = {
      title: i18n.t('actions.transactions_events.task.title').toString(),
      description: i18n
        .t('actions.transactions_events.task.description')
        .toString(),
      numericKeys: []
    };

    const { result } = await awaitTask(taskId, taskType, taskMeta, true);

    if (result) {
      await fetchTransactions();
    }

    const fetched = get(fetchedTxHashesEvents);
    if (isFetchAll) {
      set(fetchedTxHashesEvents, {});
    } else if (fetched && txHashesToFetch) {
      txHashesToFetch.forEach((txHash: string) => {
        delete fetched[txHash];
      });
      set(fetchedTxHashesEvents, fetched);
    }
  };

  const getTransactionsNotesWords = (
    transactions: EthTransactionEntry[]
  ): string[] => {
    return transactions
      .map(transaction => {
        return transaction.decodedEvents!.map(event => {
          return event.entry.notes;
        });
      })
      .flat()
      .join(' ')
      .split(/\s|\\n/);
  };

  const getNotesAddresses = (transactions: EthTransactionEntry[]): string[] =>
    filterAddressesFromWords(getTransactionsNotesWords(transactions));

  const reset = () => {
    set(transactions, defaultCollectionState<EthTransactionEntry>());
    set(fetchedTxHashesEvents, {});
    set(transactionsPayload, defaultHistoricPayloadState<EthTransaction>());
    set(counterparties, []);
  };

  const fetchCounterparties = async () => {
    const result = await api.history.fetchAvailableCounterparties();

    set(counterparties, result);
  };

  return {
    transactions,
    transactionsPayload,
    counterparties,
    updateTransactionsPayload,
    fetchTransactions,
    fetchTransactionEvents,
    addTransactionEvent,
    editTransactionEvent,
    deleteTransactionEvent,
    fetchCounterparties,
    reset
  };
});

export const useLedgerActions = defineStore('history/ledgerActions', () => {
  const { fetchAssociatedLocations } = useHistory();

  const ledgerActions = ref(defaultCollectionState<LedgerActionEntry>()) as Ref<
    Collection<LedgerActionEntry>
  >;

  const ledgerActionsPayload = ref<Partial<LedgerActionRequestPayload>>(
    defaultHistoricPayloadState<LedgerAction>()
  );

  const fetchLedgerActions = async (
    refresh: boolean = false,
    onlyLocation?: SupportedExchange
  ) => {
    const { awaitTask, isTaskRunning } = useTasks();
    const { setStatus, loading, isFirstLoad, resetStatus } = getStatusUpdater(
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
        ascending: [false],
        orderByAttributes: ['timestamp'],
        onlyCache
      };

      const payload: LedgerActionRequestPayload = Object.assign(
        defaults,
        parameters ?? get(ledgerActionsPayload)
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
        get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
      );

      const parsedResult = LedgerActionCollectionResponse.parse(result);
      return mapCollectionEntriesWithMeta<LedgerAction>(
        mapCollectionResponse(parsedResult)
      ) as Collection<LedgerActionEntry>;
    };

    try {
      const firstLoad = isFirstLoad();
      const onlyCache = firstLoad ? false : !refresh;
      if ((get(isTaskRunning(taskType)) || loading()) && !onlyCache) {
        return;
      }

      if (firstLoad || refresh) {
        fetchAssociatedLocations().then();
      }

      const fetchOnlyCache = async () => {
        set(ledgerActions, await fetchLedgerActionsHandler(true));
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
        get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
      );
    } catch (e) {
      logger.error(e);
      resetStatus();
    }
  };

  const updateLedgerActionsPayload = (
    newPayload: Partial<LedgerActionRequestPayload>
  ) => {
    if (!isEqual(get(ledgerActionsPayload), newPayload)) {
      set(ledgerActionsPayload, newPayload);
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
    set(ledgerActions, defaultCollectionState<LedgerActionEntry>());
    set(ledgerActionsPayload, defaultHistoricPayloadState<LedgerAction>());
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

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useHistory, import.meta.hot));
  import.meta.hot.accept(acceptHMRUpdate(useTrades, import.meta.hot));
  import.meta.hot.accept(acceptHMRUpdate(useTransactions, import.meta.hot));
  import.meta.hot.accept(acceptHMRUpdate(useLedgerActions, import.meta.hot));
  import.meta.hot.accept(acceptHMRUpdate(useAssetMovements, import.meta.hot));
}
