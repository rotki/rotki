import groupBy from 'lodash/groupBy';
import { type MaybeRef } from '@vueuse/core';
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type Collection, type CollectionResponse } from '@/types/collection';
import { type EntryWithMeta } from '@/types/history/meta';
import {
  type AddTransactionHashPayload,
  type EthTransaction,
  type EthTransactionEntry,
  type EthTransactionEvent,
  type EvmChainAddress,
  type NewEthTransactionEvent,
  type TransactionHashAndEvmChainPayload,
  type TransactionRequestPayload
} from '@/types/history/tx';
import { Section, Status } from '@/types/status';
import {
  BackendCancelledTaskError,
  type PendingTask,
  type TaskMeta
} from '@/types/task';
import { TaskType } from '@/types/task-type';
import { mapCollectionResponse } from '@/utils/collection';
import { logger } from '@/utils/logging';
import {
  filterAddressesFromWords,
  mapCollectionEntriesWithMeta
} from '@/utils/history';
import { startPromise } from '@/utils';
import { type ActionStatus } from '@/types/action';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';

export const useTransactions = () => {
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const {
    fetchEthTransactions,
    fetchEthTransactionsTask,
    deleteTransactionEvent: deleteTransactionEventCaller,
    fetchEthTransactionEvents,
    reDecodeMissingTransactionEvents,
    addTransactionEvent: addTransactionEventCaller,
    editTransactionEvent: editTransactionEventCaller,
    addTransactionHash: addTransactionHashCaller
  } = useTransactionsApi();
  const { awaitTask, isTaskRunning } = useTaskStore();

  const { removeQueryStatus, resetQueryStatus } = useTxQueryStatusStore();
  const { fetchEnsNames } = useAddressesNamesStore();

  const { txEvmChains, getEvmChainName, supportsTransactions } =
    useSupportedChains();
  const { accounts } = useAccountBalances();

  const syncTransactionTask = async (
    account: EvmChainAddress
  ): Promise<boolean> => {
    const taskType = TaskType.TX;
    const { setStatus } = useStatusUpdater(Section.TX);
    const defaults: TransactionRequestPayload = {
      limit: 0,
      offset: 0,
      ascending: [false],
      orderByAttributes: ['timestamp'],
      onlyCache: false,
      accounts: [account]
    };

    const { taskId } = await fetchEthTransactionsTask(defaults);
    const taskMeta = {
      title: t('actions.transactions.task.title').toString(),
      description: t('actions.transactions.task.description', {
        address: account.address,
        chain: account.evmChain
      }).toString()
    };

    try {
      await awaitTask<
        CollectionResponse<EntryWithMeta<EthTransaction>>,
        TaskMeta
      >(taskId, taskType, taskMeta, true);
      return true;
    } catch (e: any) {
      if (e instanceof BackendCancelledTaskError) {
        logger.debug(e);
        removeQueryStatus(account);
      } else {
        notify({
          title: t('actions.transactions.error.title').toString(),
          message: t('actions.transactions.error.description', {
            error: e,
            address: account.address,
            chain: account.evmChain
          }).toString(),
          display: true
        });
      }
    } finally {
      setStatus(
        get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
      );
    }
    return false;
  };

  const refreshTransactions = async (
    chains: Blockchain[],
    userInitiated = false
  ): Promise<void> => {
    const { setStatus, resetStatus, fetchDisabled } = useStatusUpdater(
      Section.TX
    );

    if (fetchDisabled(userInitiated)) {
      logger.info('skipping transaction refresh');
      return;
    }

    const txAccounts: EvmChainAddress[] = get(accounts)
      .filter(({ chain }) => {
        return (
          supportsTransactions(chain) &&
          (chains.length === 0 || chains.includes(chain))
        );
      })
      .map(({ address, chain }) => ({
        address,
        evmChain: getEvmChainName(chain)!
      }));

    setStatus(Status.REFRESHING);
    resetQueryStatus();

    try {
      await Promise.all(txAccounts.map(syncTransactionTask));
      startPromise(checkTransactionsMissingEvents());
      setStatus(
        get(isTaskRunning(TaskType.TX)) ? Status.REFRESHING : Status.LOADED
      );
    } catch (e) {
      logger.error(e);
      resetStatus();
    }
  };

  const fetchTransactions = async (
    payload: MaybeRef<TransactionRequestPayload>
  ): Promise<Collection<EthTransactionEntry>> => {
    const result = await fetchEthTransactions({
      ...get(payload),
      onlyCache: true
    });
    const mapped = mapCollectionEntriesWithMeta<EthTransactionEntry>(
      mapCollectionResponse(result)
    );

    startPromise(
      Promise.allSettled([
        fetchEnsNames(getNotesAddresses(mapped.data)),
        fetchTransactionEvents(
          mapped.data.filter(
            ({ decodedEvents }) => decodedEvents && decodedEvents.length === 0
          )
        )
      ])
    );
    return mapped;
  };

  const addTransactionEvent = async (
    event: NewEthTransactionEvent
  ): Promise<ActionStatus<ValidationErrors | string>> => {
    let success = false;
    let message: ValidationErrors | string = '';
    try {
      await addTransactionEventCaller(event);
      success = true;
    } catch (e: any) {
      message = e.message;
      if (e instanceof ApiValidationError) {
        message = e.getValidationErrors(event);
      }
    }

    return { success, message };
  };

  const editTransactionEvent = async (
    event: EthTransactionEvent
  ): Promise<ActionStatus<ValidationErrors | string>> => {
    let success = false;
    let message: ValidationErrors | string = '';
    try {
      await editTransactionEventCaller(event);
      success = true;
    } catch (e: any) {
      message = e.message;
      if (e instanceof ApiValidationError) {
        message = e.getValidationErrors(event);
      }
    }

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

      await awaitTask(taskId, taskType, taskMeta, true);
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
      if (transactions.length === 0) {
        return;
      }

      payloads = Object.entries(groupBy(transactions, 'evmChain')).map(
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

    await awaitTask(taskId, taskType, taskMeta, true);
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

  const addTransactionHash = async (
    payload: AddTransactionHashPayload
  ): Promise<ActionStatus<ValidationErrors | string>> => {
    let success = false;
    let message: ValidationErrors | string = '';
    try {
      await addTransactionHashCaller(payload);
      success = true;
    } catch (e: any) {
      message = e.message;
      if (e instanceof ApiValidationError) {
        message = e.getValidationErrors(payload);
      }
    }

    return { success, message };
  };

  return {
    fetchTransactions,
    refreshTransactions,
    fetchTransactionEvents,
    addTransactionEvent,
    editTransactionEvent,
    deleteTransactionEvent,
    checkTransactionsMissingEvents,
    addTransactionHash
  };
};
