import { groupBy } from 'es-toolkit';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useHistoryTransactionDecoding } from '@/composables/history/events/tx/decoding';
import { useSupportedChains } from '@/composables/info/chains';
import { useStatusUpdater } from '@/composables/status';
import { useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { type BlockchainAddress, type ChainAddress, type TransactionChainType, TransactionChainTypeNeedDecoding, type TransactionRequestPayload } from '@/types/history/events';
import { Section, Status } from '@/types/status';
import { BackendCancelledTaskError, type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { LimitedParallelizationQueue } from '@/utils/limited-parallelization-queue';
import { logger } from '@/utils/logging';

interface TransactionSyncParams {
  accounts: ChainAddress[];
  type: TransactionChainType;
}

interface UseTransactionSyncReturn {
  syncAndReDecodeEvents: (chain: string, params: TransactionSyncParams) => Promise<void>;
  syncTransactionTask: (account: ChainAddress, type: TransactionChainType) => Promise<void>;
  syncTransactionsByChains: (params: TransactionSyncParams) => Promise<void>;
}

export function useTransactionSync(): UseTransactionSyncReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notify } = useNotificationsStore();
  const queue = new LimitedParallelizationQueue(1);
  const { fetchTransactionsTask } = useHistoryEventsApi();

  const { awaitTask, isTaskRunning } = useTaskStore();
  const { removeQueryStatus } = useTxQueryStatusStore();
  const { getChainName } = useSupportedChains();
  const { setStatus } = useStatusUpdater(Section.HISTORY);
  const { decodeTransactionsTask } = useHistoryTransactionDecoding();

  const syncTransactionTask = async (
    account: ChainAddress,
    type: TransactionChainType,
  ): Promise<void> => {
    const taskType = TaskType.TX;
    const { address, chain } = account;

    const blockchainAccount: BlockchainAddress = {
      address,
      blockchain: chain,
    };
    const defaults: TransactionRequestPayload = {
      accounts: [blockchainAccount],
    };

    const chainName = get(getChainName(chain));
    const { taskId } = await fetchTransactionsTask(defaults);
    const taskMeta = {
      address,
      chain,
      description: t('actions.transactions.task.description', {
        address,
        chain: chainName,
      }),
      title: t('actions.transactions.task.title'),
      type,
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
            address,
            chain: chainName,
            error,
          }),
          title: t('actions.transactions.error.title'),
        });
      }
    }
    finally {
      setStatus(isTaskRunning(taskType, { type }) ? Status.REFRESHING : Status.LOADED);
    }
  };

  const syncAndReDecodeEvents = async (
    chain: string,
    params: TransactionSyncParams,
  ): Promise<void> => {
    const { accounts, type } = params;
    logger.debug(`syncing ${chain} transactions for ${accounts.length} addresses`);

    const getAccountKey = (item: ChainAddress): string => item.chain + item.address;

    await awaitParallelExecution(
      accounts,
      getAccountKey,
      async item => syncTransactionTask(item, type),
      2,
    );

    if (TransactionChainTypeNeedDecoding.includes(type)) {
      logger.debug(`queued ${chain} transactions for decoding`);
      queue.queue(chain, async () => {
        await decodeTransactionsTask(chain);
        logger.debug(`finished decoding ${chain} transactions`);
      });
    }
  };

  const syncTransactionsByChains = async (
    params: TransactionSyncParams,
  ): Promise<void> => {
    const { accounts, type } = params;
    logger.debug(`refreshing ${type} transactions for ${accounts.length} addresses`);

    const groupedByChains = Object.entries(groupBy(accounts, item => item.chain));

    await awaitParallelExecution(
      groupedByChains,
      ([chain]) => chain,
      async ([chain, data]) => syncAndReDecodeEvents(chain, { accounts: data, type }),
      2,
    );

    if (accounts.length > 0)
      setStatus(isTaskRunning(TaskType.TX, { type }) ? Status.REFRESHING : Status.LOADED);
    logger.debug(`finished refreshing ${type} transactions for ${accounts.length} addresses`);
  };

  return {
    syncAndReDecodeEvents,
    syncTransactionsByChains,
    syncTransactionTask,
  };
}
