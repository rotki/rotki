import isEqual from 'lodash/isEqual';
import { Ref } from 'vue';
import { useStatusUpdater } from '@/composables/status';
import { api } from '@/services/rotkehlchen-api';
import { useEthNamesStore } from '@/store/balances/ethereum-names';
import { useEthBalancesStore } from '@/store/blockchain/balances/eth';
import { EthTransactionEntry } from '@/store/history/types';
import {
  defaultHistoricPayloadState,
  filterAddressesFromWords,
  mapCollectionEntriesWithMeta
} from '@/store/history/utils';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { Collection, CollectionResponse } from '@/types/collection';
import { EntryWithMeta } from '@/types/history/meta';
import { TradeRequestPayload } from '@/types/history/trades';
import {
  EthTransaction,
  EthTransactionCollectionResponse,
  NewEthTransactionEvent,
  TransactionRequestPayload
} from '@/types/history/tx';
import { Section, Status } from '@/types/status';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import {
  defaultCollectionState,
  mapCollectionResponse
} from '@/utils/collection';
import { logger } from '@/utils/logging';

export const useTransactions = defineStore('history/transactions', () => {
  const transactions = ref(
    defaultCollectionState<EthTransactionEntry>()
  ) as Ref<Collection<EthTransactionEntry>>;

  const fetchedTxHashesEvents: Ref<Record<string, boolean> | null> = ref({});
  const transactionsPayload: Ref<Partial<TransactionRequestPayload>> = ref(
    defaultHistoricPayloadState<EthTransaction>()
  );

  const counterparties = ref<string[]>([]);

  const { t } = useI18n();

  const { ethAddresses } = storeToRefs(useEthBalancesStore());
  const fetchTransactions = async (refresh: boolean = false) => {
    const { awaitTask, isTaskRunning } = useTasks();
    const { setStatus, loading, isFirstLoad, resetStatus } = useStatusUpdater(
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
        await fetchEnsNames(addresses, false);

        return mapped;
      }

      const { taskId } = await api.history.ethTransactionsTask(payload);
      const address = parameters?.address ?? '';
      const taskMeta = {
        title: t('actions.transactions.task.title').toString(),
        description: address
          ? t('actions.transactions.task.description', {
              address
            }).toString()
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
              title: t('actions.transactions.error.title').toString(),
              message: t('actions.transactions.error.description', {
                error,
                address
              }).toString(),
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

  const updateTransactionsPayload = async (
    newPayload: Partial<TransactionRequestPayload>
  ) => {
    if (!isEqual(get(transactionsPayload), newPayload)) {
      set(transactionsPayload, newPayload);
      await fetchTransactions();
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
      title: t('actions.transactions_events.task.title').toString(),
      description: t('actions.transactions_events.task.description').toString(),
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
    fetchCounterparties
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useTransactions, import.meta.hot));
}
