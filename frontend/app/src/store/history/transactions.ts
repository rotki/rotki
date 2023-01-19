import isEqual from 'lodash/isEqual';
import { type Ref } from 'vue';
import { groupBy } from 'lodash';
import { useHistoryApi } from '@/services/history';
import { useTransactionsApi } from '@/services/history/transactions';
import { type PendingTask } from '@/services/types-api';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useTxQueryStatusStore } from '@/store/history/query-status';
import { useNotificationsStore } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { type ActionStatus } from '@/store/types';
import { type Collection, type CollectionResponse } from '@/types/collection';
import { type EntryWithMeta } from '@/types/history/meta';
import { type TradeRequestPayload } from '@/types/history/trades';
import {
  type EthTransaction,
  EthTransactionCollectionResponse,
  type EthTransactionEntry,
  type NewEthTransactionEvent,
  type TransactionHashAndEvmChainPayload,
  type TransactionRequestPayload
} from '@/types/history/tx';
import { Section, Status } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import {
  defaultCollectionState,
  mapCollectionResponse
} from '@/utils/collection';
import { logger } from '@/utils/logging';
import { useAccountBalancesStore } from '@/store/blockchain/accountbalances';
import {
  defaultHistoricPayloadState,
  filterAddressesFromWords,
  mapCollectionEntriesWithMeta
} from '@/utils/history';

export const useTransactions = defineStore('history/transactions', () => {
  const transactions: Ref<Collection<EthTransactionEntry>> = ref(
    defaultCollectionState<EthTransactionEntry>()
  );

  const transactionsPayload: Ref<Partial<TransactionRequestPayload>> = ref(
    defaultHistoricPayloadState<EthTransaction>()
  );
  const fetchedTxAccounts: Ref<{ address: string; evmChain: string }[]> = ref(
    []
  );

  const decodedTxEvents: Ref<string[]> = ref([]);

  const counterparties = ref<string[]>([]);

  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const {
    fetchEthTransactions,
    fetchEthTransactionsTask,
    deleteTransactionEvent: deleteTransactionEventCaller,
    fetchEthTransactionEvents,
    reDecodeMissingTransactionEvents
  } = useTransactionsApi();
  const { awaitTask, isTaskRunning } = useTasks();

  const { fetchAvailableCounterparties } = useHistoryApi();
  const { resetQueryStatus } = useTxQueryStatusStore();

  const { txEvmChains, getEvmChainName, supportsTransactions } =
    useSupportedChains();
  const { accounts } = storeToRefs(useAccountBalancesStore());

  const fetchTransactions = async (refresh = false): Promise<void> => {
    const { setStatus, loading, isFirstLoad, resetStatus } = useStatusUpdater(
      Section.TX
    );
    const taskType = TaskType.TX;

    const fetchTransactionsHandler = async (
      onlyCache: boolean,
      parameters?: Partial<TransactionRequestPayload>
    ): Promise<Collection<EthTransactionEntry>> => {
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

      const { fetchEnsNames } = useAddressesNamesStore();
      if (onlyCache) {
        const result = await fetchEthTransactions(payload);

        const mapped = mapCollectionEntriesWithMeta<EthTransaction>(
          mapCollectionResponse(result)
        );

        const addresses = getNotesAddresses(mapped.data);
        await fetchEnsNames(addresses);

        return mapped;
      }

      const { taskId } = await fetchEthTransactionsTask(payload);
      const address = parameters?.address ?? '';
      const taskMeta = {
        title: t('actions.transactions.task.title').toString(),
        description: address
          ? t('actions.transactions.task.description', {
              address
            }).toString()
          : undefined,
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
      );
    };

    try {
      const firstLoad = isFirstLoad();
      const accountsList = get(accounts)
        .filter(({ chain }) => supportsTransactions(chain))
        .map(({ address, chain }) => ({
          address,
          evmChain: getEvmChainName(chain)!
        }));
      const accountsUpdated = !isEqual(accountsList, get(fetchedTxAccounts));
      const onlyCache = firstLoad || accountsUpdated ? false : !refresh;
      if ((get(isTaskRunning(taskType)) || loading()) && !onlyCache) {
        return;
      }

      const fetchOnlyCache = async (): Promise<void> => {
        set(transactions, await fetchTransactionsHandler(true));
      };

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      await fetchOnlyCache();

      if (!onlyCache) {
        setStatus(Status.REFRESHING);
        resetQueryStatus();
        set(fetchedTxAccounts, accountsList);
        const refreshAddressTxs = accountsList.map(account =>
          fetchTransactionsHandler(false, account).catch(error => {
            notify({
              title: t('actions.transactions.error.title').toString(),
              message: t('actions.transactions.error.description', {
                error,
                address: account.address
              }).toString(),
              display: true
            });
          })
        );
        await Promise.all(refreshAddressTxs);
        await checkTransactionsMissingEvents();
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
  ): Promise<void> => {
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
      await addTransactionEvent(event);
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
      await editTransactionEvent(event);
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
      success = await deleteTransactionEventCaller([eventId]);
    } catch (e: any) {
      message = e.message;
    }

    await fetchTransactions();
    return { success, message };
  };

  const checkTransactionsMissingEvents = async () => {
    try {
      const taskType = TaskType.TX_EVENTS;
      const { taskId } = await reDecodeMissingTransactionEvents<PendingTask>(
        get(txEvmChains).map(chain => ({ evmChain: chain.evmChainName }))
      );

      const taskMeta = {
        title: t('actions.transactions_events.task.title').toString(),
        description: t(
          'actions.transactions_events.task.description'
        ).toString(),
        numericKeys: []
      };

      const { result } = await awaitTask(taskId, taskType, taskMeta, true);

      if (result) {
        await fetchTransactions();
      }
    } catch (e) {
      logger.error(e);
    }
  };

  const fetchTransactionEvents = async (
    transactions: EthTransactionEntry[] | null,
    ignoreCache = false
  ): Promise<void> => {
    const isFetchAll = transactions === null;

    let payloads: TransactionHashAndEvmChainPayload[] = [];

    if (isFetchAll) {
      payloads = get(txEvmChains).map(chain => ({
        evmChain: chain.evmChainName
      }));
    } else {
      if (transactions.length === 0) return;
      const decodedTxEventsVal = [...get(decodedTxEvents)];
      const mapped = transactions
        .filter(({ evmChain, txHash }) => {
          const key = evmChain + txHash;
          const decoded = decodedTxEventsVal.includes(key);

          if (decoded) {
            return false;
          }
          decodedTxEventsVal.push(key);
          set(decodedTxEvents, decodedTxEventsVal);

          return true;
        })
        .map(({ evmChain, txHash }) => ({
          evmChain,
          txHash
        }));

      if (mapped.length === 0) return;

      payloads = Object.entries(groupBy(mapped, 'evmChain')).map(
        ([evmChain, item]) => ({
          evmChain,
          txHashes: item.map(({ txHash }) => txHash)
        })
      );
    }

    const taskType = TaskType.TX_EVENTS;
    const { taskId } = await fetchEthTransactionEvents({
      data: payloads,
      ignoreCache
    });
    const taskMeta = {
      title: t('actions.transactions_events.task.title').toString(),
      description: t('actions.transactions_events.task.description').toString()
    };

    const { result } = await awaitTask(taskId, taskType, taskMeta, true);

    if (result) {
      const decodedTxEventsVal = [...get(decodedTxEvents)];
      payloads.forEach(payload => {
        if (payload.txHashes) {
          payload.txHashes.forEach(txHash => {
            const key = payload.evmChain + txHash;
            decodedTxEventsVal.splice(decodedTxEventsVal.indexOf(key), 1);
          });
        }
      });
      set(decodedTxEvents, decodedTxEventsVal);
      await fetchTransactions();
    }
  };

  const getTransactionsNotesWords = (
    transactions: EthTransactionEntry[]
  ): string[] => {
    return transactions
      .flatMap(transaction => {
        return transaction.decodedEvents!.map(event => {
          return event.entry.notes;
        });
      })
      .join(' ')
      .split(/\s|\\n/);
  };

  const getNotesAddresses = (transactions: EthTransactionEntry[]): string[] =>
    filterAddressesFromWords(getTransactionsNotesWords(transactions));

  const fetchCounterparties = async (): Promise<void> => {
    const result = await fetchAvailableCounterparties();

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
    checkTransactionsMissingEvents
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useTransactions, import.meta.hot));
}
