import { groupBy } from 'lodash-es';
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
import type { ActionStatus } from '@/types/action';
import type { Blockchain } from '@rotki/common';

export const useHistoryTransactions = createSharedComposable(() => {
  const { t } = useI18n();
  const { notify } = useNotificationsStore();
  const queue = new LimitedParallelizationQueue(2);

  const {
    fetchTransactionsTask,
    addTransactionHash: addTransactionHashCaller,
    queryOnlineHistoryEvents,
  } = useHistoryEventsApi();

  const { addresses } = storeToRefs(useBlockchainStore());
  const { awaitTask, isTaskRunning } = useTaskStore();
  const { removeQueryStatus, resetQueryStatus } = useTxQueryStatusStore();
  const { getEvmChainName, supportsTransactions, isEvmLikeChains, getChainName } = useSupportedChains();
  const { setStatus, resetStatus, fetchDisabled } = useStatusUpdater(Section.HISTORY_EVENT);
  const { decodeTransactionsTask, fetchUndecodedTransactionsStatus } = useHistoryTransactionDecoding();
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
      title: t('actions.transactions.task.title'),
      description: t('actions.transactions.task.description', {
        address: account.address,
        chain: get(getChainName(account.evmChain)),
      }),
      isEvm,
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
          title: t('actions.transactions.error.title'),
          message: t('actions.transactions.error.description', {
            error,
            address: account.address,
            chain: toHumanReadable(account.evmChain),
          }),
          display: true,
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
      item => syncTransactionTask(item, type),
    );
    queue.queue(evmChain, () => decodeTransactionsTask(evmChain, type));
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
      title: t('actions.online_events.task.title'),
      description: t('actions.online_events.task.description', {
        queryType,
      }),
      queryType,
    };

    try {
      await awaitTask<boolean, TaskMeta>(taskId, taskType, taskMeta, true);
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        notify({
          title: t('actions.online_events.error.title'),
          message: t('actions.online_events.error.description', {
            error,
            queryType,
          }),
          display: true,
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
        evmChain,
        data,
      }),
    );

    await awaitParallelExecution(
      groupedByChains,
      item => item.evmChain,
      item => syncAndReDecodeEvents(item.evmChain, item.data, type),
    );

    const isEvm = type === TransactionChainType.EVM;
    if (addresses.length > 0)
      setStatus(get(isTaskRunning(TaskType.TX, { isEvm })) ? Status.REFRESHING : Status.LOADED);
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
        queryOnlineEvent(OnlineHistoryEventsQueryType.EXCHANGES),
      ]);

      if (!disableEvmEvents)
        await fetchUndecodedTransactionsStatus();
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

    return { success, message };
  };

  return {
    refreshTransactions,
    addTransactionHash,
  };
});
