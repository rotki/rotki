import groupBy from 'lodash/groupBy';
import { type MaybeRef } from '@vueuse/core';
import { type Blockchain } from '@rotki/common/lib/blockchain';
import omit from 'lodash/omit';
import { type Collection, type CollectionResponse } from '@/types/collection';
import { type EntryWithMeta } from '@/types/history/meta';
import {
  type AddTransactionHashPayload,
  type AddressesAndEvmChainPayload,
  type EditEvmHistoryEventPayload,
  type EvmChainAddress,
  type EvmChainAndTxHash,
  type EvmTransaction,
  type HistoryEventEntry,
  type HistoryEventEntryWithMeta,
  type HistoryEventRequestPayload,
  type HistoryEventsCollectionResponse,
  type NewEvmHistoryEventPayload,
  OnlineHistoryEventsQueryType,
  type TransactionHashAndEvmChainPayload,
  type TransactionRequestPayload
} from '@/types/history/events';
import { Section, Status } from '@/types/status';
import {
  BackendCancelledTaskError,
  type PendingTask,
  type TaskMeta
} from '@/types/task';
import { TaskType } from '@/types/task-type';
import { type ActionStatus } from '@/types/action';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { Module } from '@/types/modules';
import { defaultCollectionState } from '@/utils/collection';

export const useHistoryEvents = () => {
  const { t, tc } = useI18n();
  const { notify } = useNotificationsStore();

  const {
    fetchEvmTransactionsTask,
    deleteTransactionEvent: deleteTransactionEventCaller,
    decodeHistoryEvents,
    reDecodeMissingTransactionEvents,
    addTransactionEvent: addTransactionEventCaller,
    editTransactionEvent: editTransactionEventCaller,
    addTransactionHash: addTransactionHashCaller,
    fetchHistoryEvents: fetchHistoryEventsCaller,
    queryOnlineHistoryEvents
  } = useHistoryEventsApi();

  const { awaitTask, isTaskRunning } = useTaskStore();

  const { removeQueryStatus, resetQueryStatus } = useTxQueryStatusStore();

  const { txEvmChains, getEvmChainName, supportsTransactions } =
    useSupportedChains();
  const { accounts } = useAccountBalances();

  const { setStatus, resetStatus, fetchDisabled } = useStatusUpdater(
    Section.TX
  );

  const syncTransactionTask = async (
    account: EvmChainAddress
  ): Promise<boolean> => {
    const taskType = TaskType.TX;
    const defaults: TransactionRequestPayload = {
      limit: 0,
      offset: 0,
      ascending: [false],
      orderByAttributes: ['timestamp'],
      onlyCache: false,
      accounts: [account]
    };

    const { taskId } = await fetchEvmTransactionsTask(defaults);
    const taskMeta = {
      title: t('actions.transactions.task.title').toString(),
      description: t('actions.transactions.task.description', {
        address: account.address,
        chain: account.evmChain
      }).toString()
    };

    try {
      await awaitTask<
        CollectionResponse<EntryWithMeta<EvmTransaction>>,
        TaskMeta
      >(taskId, taskType, taskMeta, true);
      startPromise(reDecodeMissingTransactionEventsTask(account));
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
    if (fetchDisabled(userInitiated)) {
      logger.info('skipping transaction refresh');
      return;
    }

    const txAccounts: EvmChainAddress[] = get(accounts)
      .filter(
        ({ chain }) =>
          supportsTransactions(chain) &&
          (chains.length === 0 || chains.includes(chain))
      )
      .map(({ address, chain }) => ({
        address,
        evmChain: getEvmChainName(chain)!
      }));

    setStatus(Status.REFRESHING);
    resetQueryStatus();

    try {
      await Promise.all([
        ...txAccounts.map(syncTransactionTask),
        queryOnlineEvent(OnlineHistoryEventsQueryType.ETH_WITHDRAWALS),
        queryOnlineEvent(OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS),
        queryOnlineEvent(OnlineHistoryEventsQueryType.EXCHANGES)
      ]);
      setStatus(
        get(isTaskRunning(TaskType.TX)) ? Status.REFRESHING : Status.LOADED
      );
    } catch (e) {
      logger.error(e);
      resetStatus();
    }
  };

  const { isModuleEnabled } = useModules();
  const isEth2Enabled = isModuleEnabled(Module.ETH2);

  const queryOnlineEvent = async (queryType: OnlineHistoryEventsQueryType) => {
    const eth2QueryTypes = [
      OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
      OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS
    ];

    if (!get(isEth2Enabled) && eth2QueryTypes.includes(queryType)) {
      return;
    }
    const taskType = TaskType.QUERY_ONLINE_EVENTS;

    const { taskId } = await queryOnlineHistoryEvents({
      asyncQuery: true,
      queryType
    });

    const taskMeta = {
      title: t('actions.online_events.task.title').toString(),
      description: t('actions.online_events.task.description', {
        queryType
      }).toString(),
      queryType
    };

    try {
      await awaitTask<boolean, TaskMeta>(taskId, taskType, taskMeta, true);
    } catch (e: any) {
      logger.error(e);
      notify({
        title: t('actions.online_events.error.title').toString(),
        message: t('actions.online_events.error.description', {
          error: e,
          queryType
        }).toString(),
        display: true
      });
    }
  };

  const reDecodeMissingTransactionEventsTask = async (
    account: EvmChainAddress
  ) => {
    const taskType = TaskType.TX_EVENTS;

    const payload: AddressesAndEvmChainPayload = {
      evmChain: account.evmChain,
      addresses: [account.address]
    };

    if (get(isTaskRunning(taskType, payload))) {
      return;
    }

    try {
      const { taskId } = await reDecodeMissingTransactionEvents<PendingTask>([
        payload
      ]);

      const taskMeta = {
        title: t('actions.transactions_redecode_missing.task.title').toString(),
        description: tc(
          'actions.transactions_redecode_missing.task.description',
          0,
          account
        ),
        ...payload
      };

      await awaitTask(taskId, taskType, taskMeta, true);
    } catch (e) {
      logger.error(e);
      notify({
        title: t(
          'actions.transactions_redecode_missing.error.title'
        ).toString(),
        message: tc(
          'actions.transactions_redecode_missing.error.description',
          0,
          {
            error: e,
            ...account
          }
        ),
        display: true
      });
    }
  };

  const { fetchEnsNames } = useAddressesNamesStore();
  const fetchHistoryEvents = async (
    payload: MaybeRef<HistoryEventRequestPayload>
  ): Promise<Collection<HistoryEventEntry>> => {
    try {
      const result = await fetchHistoryEventsCaller(
        omit(get(payload), 'accounts')
      );

      const { data, ...other } = mapCollectionResponse<
        HistoryEventEntryWithMeta,
        HistoryEventsCollectionResponse
      >(result);

      const notesList: string[] = [];

      const mappedData = data.map((event: HistoryEventEntryWithMeta) => {
        const { entry, ...entriesMeta } = event;

        if (entry.notes) {
          notesList.push(entry.notes);
        }

        return {
          ...entry,
          ...entriesMeta
        };
      });

      if (!get(payload).groupByEventIds) {
        startPromise(fetchEnsNames(getEthAddressesFromText(notesList)));
      }

      return {
        ...other,
        data: mappedData
      };
    } catch (e: any) {
      logger.error(e);
      notify({
        title: t('actions.history_events.error.title').toString(),
        message: t('actions.history_events.error.description', {
          error: e
        }).toString(),
        display: true
      });
      return defaultCollectionState();
    }
  };

  const addTransactionEvent = async (
    event: NewEvmHistoryEventPayload
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
    event: EditEvmHistoryEventPayload
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

  const fetchTransactionEvents = async (
    transactions: EvmChainAndTxHash[] | null,
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

    try {
      const taskType = TaskType.TX_EVENTS;
      const { taskId } = await decodeHistoryEvents({
        data: payloads,
        ignoreCache
      });
      const taskMeta = {
        title: t('actions.transactions_redecode.task.title').toString(),
        description: t(
          'actions.transactions_redecode.task.description'
        ).toString()
      };

      await awaitTask(taskId, taskType, taskMeta, true);
    } catch (e: any) {
      logger.error(e);
      notify({
        title: t('actions.transactions_redecode.error.title').toString(),
        message: tc('actions.transactions_redecode.error.description', 0, {
          error: e
        }),
        display: true
      });
    }
  };

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
    refreshTransactions,
    fetchTransactionEvents,
    addTransactionEvent,
    editTransactionEvent,
    deleteTransactionEvent,
    addTransactionHash,
    fetchHistoryEvents
  };
};
