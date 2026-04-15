import type { TaskMeta } from '@/modules/tasks/types';
import { groupBy } from 'es-toolkit';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useHistoryTransactionDecoding } from '@/composables/history/events/tx/decoding';
import { useHistoryTransactionAccounts } from '@/composables/history/events/tx/use-history-transaction-accounts';
import { useSupportedChains } from '@/composables/info/chains';
import { type BlockchainAddress, type ChainAddress, TransactionChainType, TransactionChainTypeNeedDecoding, type TransactionRequestPayload } from '@/modules/history/events/event-payloads';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { TaskType } from '@/modules/tasks/task-type';
import { useTaskHandler } from '@/modules/tasks/use-task-handler';
import { useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { LimitedParallelizationQueue } from '@/utils/limited-parallelization-queue';
import { logger } from '@/utils/logging';

interface TransactionSyncParams {
  accounts: ChainAddress[];
  type: TransactionChainType;
  trackProgress?: boolean;
}

interface UseTransactionSyncReturn {
  syncAndReDecodeEvents: (chain: string, params: TransactionSyncParams) => Promise<void>;
  syncTransactionTask: (account: ChainAddress, type: TransactionChainType, trackProgress?: boolean) => Promise<void>;
  syncTransactionsByChains: (accounts: ChainAddress[], trackProgress?: boolean) => Promise<void>;
  waitForDecoding: () => Promise<void>;
}

export function useTransactionSync(): UseTransactionSyncReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();
  const queue = new LimitedParallelizationQueue(1);
  const { fetchTransactionsTask } = useHistoryEventsApi();

  const { runTask } = useTaskHandler();
  const { isAddressCancelled, markAddressCancelled, removeQueryStatus, setEvmlikeStatus } = useTxQueryStatusStore();
  const { getChainName } = useSupportedChains();
  const { decodeTransactionsTask } = useHistoryTransactionDecoding();
  const { getTransactionTypeFromChain } = useHistoryTransactionAccounts();

  const syncTransactionTask = async (
    account: ChainAddress,
    type: TransactionChainType,
    trackProgress = true,
  ): Promise<void> => {
    const { address, chain } = account;
    const isEvmlike = type === TransactionChainType.EVMLIKE;

    const blockchainAccount: BlockchainAddress = {
      address,
      blockchain: chain,
    };
    const defaults: TransactionRequestPayload = {
      accounts: [blockchainAccount],
    };

    // Evmlike chains don't send websocket messages, so track status manually
    // Only track when progress display is enabled
    if (isEvmlike && trackProgress)
      setEvmlikeStatus(account, 'started');

    const chainName = getChainName(chain);
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

    const outcome = await runTask<boolean, TaskMeta>(
      async () => fetchTransactionsTask(defaults),
      { type: TaskType.TX, meta: taskMeta, unique: false },
    );

    if (!outcome.success) {
      if (outcome.backendCancelled) {
        logger.debug(outcome.message);
        removeQueryStatus(account);
      }
      else if (outcome.cancelled) {
        markAddressCancelled(account);
      }
      else if (!outcome.skipped) {
        notifyError(
          t('actions.transactions.error.title'),
          t('actions.transactions.error.description', {
            address,
            chain: chainName,
            error: outcome.message,
          }),
        );
      }
    }

    // Mark evmlike as finished when the task completes (but not when cancelled)
    // setEvmlikeStatus already guards against overwriting cancelled entries
    if (isEvmlike && trackProgress)
      setEvmlikeStatus(account, 'finished');
  };

  const syncAndReDecodeEvents = async (
    chain: string,
    params: TransactionSyncParams,
  ): Promise<void> => {
    const { accounts, trackProgress = true, type } = params;
    logger.debug(`syncing ${chain} transactions for ${accounts.length} addresses`);

    const getAccountKey = (item: ChainAddress): string => item.chain + item.address;

    await awaitParallelExecution(
      accounts,
      getAccountKey,
      async item => syncTransactionTask(item, type, trackProgress),
      2,
    );

    // Skip decoding if all accounts for this chain were cancelled
    const allCancelled = accounts.every(acc => isAddressCancelled(acc));

    if (allCancelled) {
      logger.debug(`skipping decoding for ${chain} — all accounts were cancelled`);
      return;
    }

    if (TransactionChainTypeNeedDecoding.includes(type)) {
      logger.debug(`queued ${chain} transactions for decoding`);
      queue.queue(chain, async () => {
        await decodeTransactionsTask(chain);
        logger.debug(`finished decoding ${chain} transactions`);
      });
    }
  };

  const syncTransactionsByChains = async (accounts: ChainAddress[], trackProgress = true): Promise<void> => {
    logger.debug(`refreshing transactions for ${accounts.length} addresses`);

    const groupedByChains = Object.entries(groupBy(accounts, item => item.chain));

    await awaitParallelExecution(
      groupedByChains,
      ([chain]) => chain,
      async ([chain, accounts]) => {
        const type = getTransactionTypeFromChain(chain);
        await syncAndReDecodeEvents(chain, { accounts, trackProgress, type });
      },
      2,
    );
  };

  const waitForDecoding = async (): Promise<void> => new Promise((resolve) => {
    if (queue.running === 0 && queue.pending === 0) {
      resolve();
      return;
    }
    queue.setOnCompletion(() => resolve());
  });

  return {
    syncAndReDecodeEvents,
    syncTransactionsByChains,
    syncTransactionTask,
    waitForDecoding,
  };
}
