import { type Blockchain } from '@rotki/common/lib/blockchain';
import { groupBy } from 'lodash-es';
import { Section, Status } from '@/types/status';
import {
  type AddTransactionHashPayload,
  type EvmChainAddress,
  OnlineHistoryEventsQueryType,
  type TransactionRequestPayload
} from '@/types/history/events';
import { TaskType } from '@/types/task-type';
import { BackendCancelledTaskError, type TaskMeta } from '@/types/task';
import { Module } from '@/types/modules';
import { type ActionStatus } from '@/types/action';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';

export const useHistoryTransactions = createSharedComposable(() => {
  const { t } = useI18n();
  const { notify } = useNotificationsStore();
  const queue = new LimitedParallelizationQueue(4);

  const {
    fetchEvmTransactionsTask,
    addTransactionHash: addTransactionHashCaller,
    queryOnlineHistoryEvents
  } = useHistoryEventsApi();

  const { resetEvmUndecodedTransactionsStatus } = useHistoryStore();
  const { awaitTask, isTaskRunning } = useTaskStore();
  const { removeQueryStatus, resetQueryStatus } = useTxQueryStatusStore();
  const { getEvmChainName, supportsTransactions } = useSupportedChains();
  const { accounts } = useAccountBalances();
  const { setStatus, resetStatus, fetchDisabled } = useStatusUpdater(
    Section.HISTORY_EVENT
  );

  const { reDecodeMissingTransactionEventsTask } =
    useHistoryTransactionDecoding();

  const syncTransactionTask = async (
    account: EvmChainAddress
  ): Promise<void> => {
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
      title: t('actions.transactions.task.title'),
      description: t('actions.transactions.task.description', {
        address: account.address,
        chain: account.evmChain
      })
    };

    try {
      await awaitTask<boolean, TaskMeta>(taskId, taskType, taskMeta, true);
    } catch (e: any) {
      if (e instanceof BackendCancelledTaskError) {
        logger.debug(e);
        removeQueryStatus(account);
      } else if (!isTaskCancelled(e)) {
        notify({
          title: t('actions.transactions.error.title'),
          message: t('actions.transactions.error.description', {
            error: e,
            address: account.address,
            chain: toHumanReadable(account.evmChain)
          }),
          display: true
        });
      }
    } finally {
      setStatus(
        get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
      );
    }
  };

  const syncAndRedecode = async (
    evmChain: string,
    accounts: EvmChainAddress[]
  ): Promise<void> => {
    await awaitParallelExecution(
      accounts,
      item => item.evmChain + item.address,
      syncTransactionTask
    );
    queue.queue(evmChain, () => reDecodeMissingTransactionEventsTask(evmChain));
  };

  const getTxAccounts = (chains: Blockchain[] = []) =>
    get(accounts)
      .filter(
        ({ chain }) =>
          supportsTransactions(chain) &&
          (chains.length === 0 || chains.includes(chain))
      )
      .map(({ address, chain }) => ({
        address,
        evmChain: getEvmChainName(chain)!
      }));

  const refreshTransactions = async (
    chains: Blockchain[],
    disableEvmEvents = false,
    userInitiated = false
  ): Promise<void> => {
    if (fetchDisabled(userInitiated)) {
      logger.info('skipping transaction refresh');
      return;
    }

    const txAccounts: EvmChainAddress[] = disableEvmEvents
      ? []
      : getTxAccounts(chains);

    if (txAccounts.length > 0) {
      setStatus(Status.REFRESHING);
      resetQueryStatus();
      resetEvmUndecodedTransactionsStatus();
    }

    const grouppedByEvmChain = Object.entries(
      groupBy(txAccounts, account => account.evmChain)
    ).map(([evmChain, data]) => ({
      evmChain,
      data
    }));

    try {
      await Promise.all([
        awaitParallelExecution(
          grouppedByEvmChain,
          item => item.evmChain,
          item => syncAndRedecode(item.evmChain, item.data)
        ),
        queryOnlineEvent(OnlineHistoryEventsQueryType.ETH_WITHDRAWALS),
        queryOnlineEvent(OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS),
        queryOnlineEvent(OnlineHistoryEventsQueryType.EXCHANGES)
      ]);

      if (txAccounts.length > 0) {
        setStatus(
          get(isTaskRunning(TaskType.TX)) ? Status.REFRESHING : Status.LOADED
        );
      }
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
      title: t('actions.online_events.task.title'),
      description: t('actions.online_events.task.description', {
        queryType
      }),
      queryType
    };

    try {
      await awaitTask<boolean, TaskMeta>(taskId, taskType, taskMeta, true);
    } catch (e: any) {
      if (!isTaskCancelled(e)) {
        logger.error(e);
        notify({
          title: t('actions.online_events.error.title'),
          message: t('actions.online_events.error.description', {
            error: e,
            queryType
          }),
          display: true
        });
      }
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
    addTransactionHash
  };
});
