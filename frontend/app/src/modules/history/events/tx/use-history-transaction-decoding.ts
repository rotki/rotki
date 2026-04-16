import type { TaskMeta } from '@/modules/core/tasks/types';
import { groupBy } from 'es-toolkit';
import { snakeCaseTransformer } from '@/modules/core/api/transformers';
import { awaitParallelExecution } from '@/modules/core/common/async/await-parallel-execution';
import { logger } from '@/modules/core/common/logging/logging';
import { Section } from '@/modules/core/common/status';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { EvmUndecodedTransactionResponse } from '@/modules/core/messaging/types';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import {
  type PullEthBlockEventPayload,
  type PullLocationTransactionPayload,
  type PullTransactionPayload,
  TransactionChainType,
  TransactionChainTypeNeedDecoding,
} from '@/modules/history/events/event-payloads';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';
import { useStatusUpdater } from '@/modules/shell/sync-progress/use-status-updater';

export const useHistoryTransactionDecoding = createSharedComposable(() => {
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();

  const {
    decodeTransactions,
    getUndecodedTransactionsBreakdown,
    pullAndRecodeEthBlockEventRequest,
    pullAndRecodeTransactionRequest,
  } = useHistoryEventsApi();

  const { cancelTaskByTaskType, runTask } = useTaskHandler();
  const { isTaskRunning } = useTaskStore();
  const {
    markDecodingCancelled,
    resetUndecodedTransactionsStatus,
    getUndecodedTransactionStatus,
    updateUndecodedTransactionsStatus,
  } = useDecodingStatusStore();

  const { decodableTxChainsInfo, getChain, getChainName, isEvmLikeChains, isSolanaChains } = useSupportedChains();

  const { resetStatus } = useStatusUpdater(Section.HISTORY);

  const fetchUndecodedTransactionsBreakdown = async (): Promise<void> => {
    if (isTaskRunning(TaskType.FETCH_UNDECODED_TXS)) {
      logger.debug(`was already fetching undecoded transactions`);
      return;
    }

    const title = t('actions.history.fetch_undecoded_transactions.task.title');

    const outcome = await runTask<EvmUndecodedTransactionResponse, TaskMeta>(
      async () => getUndecodedTransactionsBreakdown(),
      { type: TaskType.FETCH_UNDECODED_TXS, meta: { title }, guard: false },
    );

    if (outcome.success) {
      const breakdown = EvmUndecodedTransactionResponse.parse(snakeCaseTransformer(outcome.result));

      if (Object.keys(breakdown).length > 0) {
        updateUndecodedTransactionsStatus(
          Object.fromEntries(
            Object.entries(breakdown).map(([chain, entry]) => [
              chain,
              {
                chain,
                processed: 0,
                total: entry.undecoded,
              },
            ]),
          ),
        );
      }
      else {
        resetUndecodedTransactionsStatus();
      }
    }
    else if (isActionableFailure(outcome)) {
      const description = t('actions.history.fetch_undecoded_transactions.error.message', {
        message: outcome.message,
      });
      notifyError(title, description);
    }
  };

  const fetchUndecodedTransactionsStatus = async (): Promise<void> => {
    await fetchUndecodedTransactionsBreakdown();
  };

  const clearDependedSection = (): void => {
    resetStatus({ section: Section.DEFI_LIQUITY_STAKING });
    resetStatus({ section: Section.DEFI_LIQUITY_STAKING_POOLS });
    resetStatus({ section: Section.DEFI_LIQUITY_STATISTICS });
  };

  const decodeTransactionsTask = async (
    chain: string,
    ignoreCache = false,
  ): Promise<void> => {
    const taskMeta = {
      all: false,
      chain,
      description: t('actions.transactions_redecode_by_chain.task.description', { chain: getChainName(chain) }),
      title: t('actions.transactions_redecode_by_chain.task.title'),
    };

    const outcome = await runTask(
      async () => decodeTransactions(chain, ignoreCache),
      { type: TaskType.TRANSACTIONS_DECODING, meta: taskMeta, unique: false },
    );

    if (outcome.success) {
      clearDependedSection();
    }
    else if (outcome.cancelled) {
      markDecodingCancelled(chain);
    }
    else if (!outcome.skipped) {
      logger.error(outcome.error);
      notifyError(
        t('actions.transactions_redecode_by_chain.error.title'),
        t('actions.transactions_redecode_by_chain.error.description', {
          chain: getChainName(chain),
          error: outcome.message,
        }),
      );
    }
  };

  const checkMissingEventsAndRedecodeHandler = async (type: TransactionChainType): Promise<void> => {
    const isEvmType = type === TransactionChainType.EVM;
    const chains = getUndecodedTransactionStatus()
      .filter(({ chain, processed, total }) => {
        const blockchain = getChain(chain);
        const isEvmLike = isEvmLikeChains(blockchain);
        return processed < total && isEvmType === !isEvmLike;
      })
      .map(({ chain }) => getChain(chain));
    await awaitParallelExecution(
      chains,
      item => item,
      async item => decodeTransactionsTask(item),
      2,
    );
  };

  const checkMissingEventsAndRedecode = async (): Promise<void> => {
    resetUndecodedTransactionsStatus();
    await fetchUndecodedTransactionsStatus();
    await Promise.allSettled(TransactionChainTypeNeedDecoding.map(async item => checkMissingEventsAndRedecodeHandler(item)));
  };

  const redecodeTransactions = async (chains: string[] = []): Promise<void> => {
    const decodeChains = chains.length > 0 ? chains : get(decodableTxChainsInfo).map(chain => chain.id);

    await awaitParallelExecution(
      decodeChains,
      item => item,
      async item => decodeTransactionsTask(item, true),
      2,
    );
  };

  /**
   * Core decode function that throws on failure instead of notifying.
   * Used by callers that need to handle errors themselves (e.g. conflict resolution).
   */
  const pullAndDecodeTransactionsRaw = async (payload: PullTransactionPayload): Promise<void> => {
    let taskMeta = {
      description: t('actions.transactions_redecode.task.single_description', {
        chain: getChainName(payload.chain),
        number: payload.txRefs.length,
      }),
      title: t('actions.transactions_redecode.task.title'),
    };

    if (payload.txRefs.length === 1) {
      taskMeta = {
        description: t('actions.transactions_redecode.task.description', {
          chain: payload.chain,
          tx: payload.txRefs[0],
        }),
        title: t('actions.transactions_redecode.task.title'),
      };
    }

    const outcome = await runTask<boolean, TaskMeta>(
      async () => pullAndRecodeTransactionRequest(payload),
      { type: TaskType.TRANSACTIONS_DECODING, meta: taskMeta, unique: false },
    );

    if (outcome.success) {
      if (outcome.result) {
        clearDependedSection();
      }
      else {
        throw new Error(outcome.message ?? t('actions.transactions_redecode.error.title'));
      }
    }
    else if (isActionableFailure(outcome)) {
      throw new Error(outcome.message);
    }
  };

  /**
   * Notifying wrapper — catches errors and shows notifications to the user.
   * Used by the UI redecode flow where errors are displayed as toast messages.
   */
  const pullAndDecodeTransactions = async (payload: PullTransactionPayload): Promise<void> => {
    try {
      await pullAndDecodeTransactionsRaw(payload);
    }
    catch (error: any) {
      logger.error(error);
      notifyError(
        t('actions.transactions_redecode.error.title'),
        t('actions.transactions_redecode.error.description', {
          error: error.message ?? error,
        }),
      );
    }
  };

  const pullAndRedecodeTransactions = async ({ customIndexersOrder, deleteCustom, transactions }: PullLocationTransactionPayload): Promise<void> => {
    resetUndecodedTransactionsStatus();

    const grouped = groupBy(transactions, item => item.location);
    Object.entries(grouped).forEach(([chain, transactions]) => {
      updateUndecodedTransactionsStatus({
        [chain]: {
          chain,
          processed: 0,
          total: transactions.length,
        },
      });
    });

    // Group transactions by chain type
    const chainMaps = {
      evm: new Map<string, string[]>(),
      evmLike: new Map<string, string[]>(),
      solana: new Map<string, string[]>(),
    };

    transactions.forEach((item) => {
      const chain = getChain(item.location);
      let targetMap: Map<string, string[]>;

      if (isEvmLikeChains(chain)) {
        targetMap = chainMaps.evmLike;
      }
      else if (isSolanaChains(chain)) {
        targetMap = chainMaps.solana;
      }
      else {
        targetMap = chainMaps.evm;
      }

      if (!targetMap.has(chain))
        targetMap.set(chain, []);

      targetMap.get(chain)!.push(item.txRef);
    });

    // Process all chain types in parallel
    // Note: customIndexersOrder is only passed for EVM chains
    const processChainMap = async (chainMap: Map<string, string[]>, includeIndexerOrder: boolean): Promise<void> => {
      if (chainMap.size === 0)
        return;

      await awaitParallelExecution(
        Array.from(chainMap.entries()),
        ([chain]) => chain,
        async ([chain, txRefs]) => pullAndDecodeTransactions({
          chain,
          customIndexersOrder: includeIndexerOrder ? customIndexersOrder : undefined,
          deleteCustom,
          txRefs,
        }),
        2,
      );
    };

    await processChainMap(chainMaps.evm, true);
    await processChainMap(chainMaps.solana, false);
    await processChainMap(chainMaps.evmLike, false);
  };

  const pullAndRecodeEthBlockEvents = async (payload: PullEthBlockEventPayload): Promise<void> => {
    let taskMeta = {
      description: t('actions.eth_block_events_redecoding.task.single_description', {
        number: payload.blockNumbers.length,
      }),
      title: t('actions.eth_block_events_redecoding.task.title'),
    };

    if (payload.blockNumbers.length === 1) {
      const data = payload.blockNumbers[0];
      taskMeta = {
        description: t('actions.eth_block_events_redecoding.task.description', {
          block: data,
        }),
        title: t('actions.eth_block_events_redecoding.task.title'),
      };
    }

    const outcome = await runTask<boolean, TaskMeta>(
      async () => pullAndRecodeEthBlockEventRequest(payload),
      { type: TaskType.ETH_BLOCK_EVENTS_DECODING, meta: taskMeta, unique: false },
    );

    if (outcome.success) {
      if (outcome.result)
        clearDependedSection();
    }
    else if (isActionableFailure(outcome)) {
      logger.error(outcome.error);
      notifyError(
        t('actions.eth_block_events_redecoding.error.title'),
        t('actions.eth_block_events_redecoding.error.description', {
          error: outcome.message,
        }),
      );
    }
  };

  async function cancelDecoding(): Promise<void> {
    await cancelTaskByTaskType(TaskType.TRANSACTIONS_DECODING);
  }

  return {
    cancelDecoding,
    checkMissingEventsAndRedecode,
    decodeTransactionsTask,
    fetchUndecodedTransactionsBreakdown,
    fetchUndecodedTransactionsStatus,
    pullAndDecodeTransactionsRaw,
    pullAndRecodeEthBlockEvents,
    pullAndRedecodeTransactions,
    redecodeTransactions,
  };
});
