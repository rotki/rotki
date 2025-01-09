import { groupBy, omit } from 'es-toolkit';
import { Section, Status } from '@/types/status';
import {
  type AddTransactionHashPayload,
  type EvmChainAddress,
  OnlineHistoryEventsQueryType,
  TransactionChainType,
  type TransactionRequestPayload,
} from '@/types/history/events';
import { TaskType } from '@/types/task-type';
import { BackendCancelledTaskError, type TaskMeta } from '@/types/task';
import { Module } from '@/types/modules';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { isTaskCancelled } from '@/utils';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { logger } from '@/utils/logging';
import { LimitedParallelizationQueue } from '@/utils/limited-parallelization-queue';
import { useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';
import { useHistoryStore } from '@/store/history';
import { useTaskStore } from '@/store/tasks';
import { useBlockchainStore } from '@/store/blockchain';
import { useNotificationsStore } from '@/store/notifications';
import { useModules } from '@/composables/session/modules';
import { useStatusUpdater } from '@/composables/status';
import { useSupportedChains } from '@/composables/info/chains';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useHistoryTransactionDecoding } from '@/composables/history/events/tx/decoding';
import { useExchangesStore } from '@/store/exchanges/index';
import type { ActionStatus } from '@/types/action';
import type { Blockchain } from '@rotki/common';
import type { Exchange } from '@/types/exchanges';

export const useHistoryTransactions = createSharedComposable(() => {
  const { t } = useI18n();
  const { notify } = useNotificationsStore();
  const queue = new LimitedParallelizationQueue(1);

  const {
    addTransactionHash: addTransactionHashCaller,
    fetchTransactionsTask,
    queryExchangeEvents,
    queryOnlineHistoryEvents,
  } = useHistoryEventsApi();

  const { addresses } = storeToRefs(useBlockchainStore());
  const { connectedExchanges } = storeToRefs(useExchangesStore());
  const { awaitTask, isTaskRunning } = useTaskStore();
  const { removeQueryStatus, resetQueryStatus } = useTxQueryStatusStore();
  const { getChainName, getEvmChainName, isEvmLikeChains, supportsTransactions } = useSupportedChains();
  const { fetchDisabled, resetStatus, setStatus } = useStatusUpdater(Section.HISTORY_EVENT);
  const {
    decodeTransactionsTask,
    fetchUndecodedTransactionsBreakdown,
    fetchUndecodedTransactionsStatus,
  } = useHistoryTransactionDecoding();
  const { resetUndecodedTransactionsStatus } = useHistoryStore();

  const syncTransactionTask = async (
    account: EvmChainAddress,
    type: TransactionChainType = TransactionChainType.EVM,
  ): Promise<void> => {
    const taskType = TaskType.TX;
    const isEvm = type === TransactionChainType.EVM;
    const defaults: TransactionRequestPayload = {
      accounts: [account],
    };

    const { taskId } = await fetchTransactionsTask(defaults, type);
    const taskMeta = {
      address: account.address,
      chain: account.evmChain,
      description: t('actions.transactions.task.description', {
        address: account.address,
        chain: get(getChainName(account.evmChain)),
      }),
      isEvm,
      title: t('actions.transactions.task.title'),
    };

    try {
      await awaitTask<boolean, TaskMeta>(taskId, taskType, taskMeta, true);
    }
    catch (error: any) {
      if (error instanceof BackendCancelledTaskError) {
        logger.debug(error);
        removeQueryStatus(account);
      }
      else if (!isTaskCancelled(error)) {
        notify({
          display: true,
          message: t('actions.transactions.error.description', {
            address: account.address,
            chain: toHumanReadable(account.evmChain),
            error,
          }),
          title: t('actions.transactions.error.title'),
        });
      }
    }
    finally {
      setStatus(get(isTaskRunning(taskType, { isEvm })) ? Status.REFRESHING : Status.LOADED);
    }
  };

  const syncAndReDecodeEvents = async (
    evmChain: string,
    accounts: EvmChainAddress[],
    type: TransactionChainType = TransactionChainType.EVM,
  ): Promise<void> => {
    await awaitParallelExecution(
      accounts,
      item => item.evmChain + item.address,
      async item => syncTransactionTask(item, type),
      2,
    );
    queue.queue(evmChain, async () => decodeTransactionsTask(evmChain, type));
  };

  const getEvmAccounts = (chains: string[] = []): { address: string; evmChain: string }[] =>
    Object.entries(get(addresses))
      .filter(([chain]) => supportsTransactions(chain) && (chains.length === 0 || chains.includes(chain)))
      .flatMap(([chain, addresses]) => {
        const evmChain = getEvmChainName(chain) ?? '';
        return addresses.map(address => ({
          address,
          evmChain,
        }));
      });

  const getEvmLikeAccounts = (chains: string[] = []): { address: string; evmChain: string }[] =>
    Object.entries(get(addresses))
      .filter(([chain]) => isEvmLikeChains(chain) && (chains.length === 0 || chains.includes(chain)))
      .flatMap(([evmChain, addresses]) =>
        addresses.map(address => ({
          address,
          evmChain,
        })),
      );

  const { isModuleEnabled } = useModules();
  const isEth2Enabled = isModuleEnabled(Module.ETH2);

  const queryOnlineEvent = async (queryType: OnlineHistoryEventsQueryType): Promise<void> => {
    const eth2QueryTypes = [
      OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
      OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS,
    ];

    if (!get(isEth2Enabled) && eth2QueryTypes.includes(queryType))
      return;

    const taskType = TaskType.QUERY_ONLINE_EVENTS;

    const { taskId } = await queryOnlineHistoryEvents({
      asyncQuery: true,
      queryType,
    });

    const taskMeta = {
      description: t('actions.online_events.task.description', {
        queryType,
      }),
      queryType,
      title: t('actions.online_events.task.title'),
    };

    try {
      await awaitTask<boolean, TaskMeta>(taskId, taskType, taskMeta, true);
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        notify({
          display: true,
          message: t('actions.online_events.error.description', {
            error,
            queryType,
          }),
          title: t('actions.online_events.error.title'),
        });
      }
    }
  };

  const refreshTransactionsHandler = async (
    addresses: EvmChainAddress[],
    type: TransactionChainType = TransactionChainType.EVM,
  ): Promise<void> => {
    const groupedByChains = Object.entries(groupBy(addresses, account => account.evmChain)).map(
      ([evmChain, data]) => ({
        data,
        evmChain,
      }),
    );

    await awaitParallelExecution(
      groupedByChains,
      item => item.evmChain,
      async item => syncAndReDecodeEvents(item.evmChain, item.data, type),
      2,
    );

    queue.queue(type, async () => fetchUndecodedTransactionsBreakdown(type));

    const isEvm = type === TransactionChainType.EVM;
    if (addresses.length > 0)
      setStatus(get(isTaskRunning(TaskType.TX, { isEvm })) ? Status.REFRESHING : Status.LOADED);
  };

  const queryExchange = async (payload: Exchange): Promise<void> => {
    const exchange = omit(payload, ['krakenAccountType']);
    const taskType = TaskType.QUERY_EXCHANGE_EVENTS;
    const taskMeta = {
      description: t('actions.exchange_events.task.description', exchange),
      exchange,
      title: t('actions.exchange_events.task.title'),
    };

    try {
      const { taskId } = await queryExchangeEvents(exchange);
      await awaitTask<boolean, TaskMeta>(taskId, taskType, taskMeta, true);
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        notify({
          display: true,
          message: t('actions.exchange_events.error.description', {
            error,
            ...exchange,
          }),
          title: t('actions.exchange_events.error.title'),
        });
      }
    }
  };

  const queryAllExchangeEvents = async (): Promise<void> => {
    const exchanges = get(connectedExchanges);
    const groupedExchanges = Object.entries(groupBy(exchanges, exchange => exchange.location));

    await awaitParallelExecution(
      groupedExchanges,
      ([group]) => group,
      async ([_group, exchanges]) => {
        for (const exchange of exchanges) {
          await queryExchange(exchange);
        }
      },
      2,
    );
  };

  const refreshTransactions = async (
    chains: Blockchain[] = [],
    disableEvmEvents = false,
    userInitiated = false,
  ): Promise<void> => {
    if (fetchDisabled(userInitiated)) {
      logger.info('skipping transaction refresh');
      return;
    }

    const evmAccounts: EvmChainAddress[] = disableEvmEvents ? [] : getEvmAccounts(chains);

    const evmLikeAccounts: EvmChainAddress[] = disableEvmEvents ? [] : getEvmLikeAccounts(chains);

    if (evmAccounts.length + evmLikeAccounts.length > 0) {
      setStatus(Status.REFRESHING);
      resetQueryStatus();
      resetUndecodedTransactionsStatus();
    }

    try {
      if (!disableEvmEvents)
        await fetchUndecodedTransactionsStatus();

      await Promise.allSettled([
        refreshTransactionsHandler(evmAccounts, TransactionChainType.EVM),
        refreshTransactionsHandler(evmLikeAccounts, TransactionChainType.EVMLIKE),
        queryOnlineEvent(OnlineHistoryEventsQueryType.ETH_WITHDRAWALS),
        queryOnlineEvent(OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS),
        queryAllExchangeEvents(),
      ]);

      if (!disableEvmEvents)
        queue.queue('undecoded-transactions-status-final', async () => fetchUndecodedTransactionsStatus());
    }
    catch (error) {
      logger.error(error);
      resetStatus();
    }
  };

  const addTransactionHash = async (
    payload: AddTransactionHashPayload,
  ): Promise<ActionStatus<ValidationErrors | string>> => {
    let success = false;
    let message: ValidationErrors | string = '';
    try {
      await addTransactionHashCaller(payload);
      success = true;
    }
    catch (error: any) {
      message = error.message;
      if (error instanceof ApiValidationError)
        message = error.getValidationErrors(payload);
    }

    return { message, success };
  };

  return {
    addTransactionHash,
    refreshTransactions,
  };
});
