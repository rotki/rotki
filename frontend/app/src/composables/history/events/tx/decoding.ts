import type { TaskMeta } from '@/types/task';
import { groupBy } from 'es-toolkit';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useSupportedChains } from '@/composables/info/chains';
import { useStatusUpdater } from '@/composables/status';
import { EvmUndecodedTransactionResponse } from '@/modules/messaging/types';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { useHistoryStore } from '@/store/history';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import {
  type PullEthBlockEventPayload,
  type PullEvmTransactionPayload,
  type PullTransactionPayload,
  TransactionChainType,
  TransactionChainTypeNeedDecoding,
} from '@/types/history/events';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { logger } from '@/utils/logging';

export const useHistoryTransactionDecoding = createSharedComposable(() => {
  const { t } = useI18n({ useScope: 'global' });
  const { notify } = useNotificationsStore();

  const {
    decodeTransactions,
    getUndecodedTransactionsBreakdown,
    pullAndRecodeEthBlockEventRequest,
    pullAndRecodeTransactionRequest,
  } = useHistoryEventsApi();

  const { awaitTask, isTaskRunning } = useTaskStore();
  const {
    clearUndecodedTransactionsNumbers,
    getUndecodedTransactionStatus,
    resetUndecodedTransactionsStatus,
    updateUndecodedTransactionsStatus,
  } = useHistoryStore();

  const { evmAndEvmLikeTxChainsInfo, getChain, getChainName, isEvmLikeChains } = useSupportedChains();

  const { resetStatus } = useStatusUpdater(Section.HISTORY);

  const fetchUndecodedTransactionsBreakdown = async (): Promise<void> => {
    const taskType = TaskType.FETCH_UNDECODED_TXS;
    if (isTaskRunning(taskType)) {
      logger.debug(`was already fetching undecoded transactions`);
      return;
    }

    const title = t('actions.history.fetch_undecoded_transactions.task.title');

    const taskMeta = {
      title,
    };

    try {
      const { taskId } = await getUndecodedTransactionsBreakdown();
      const { result } = await awaitTask<EvmUndecodedTransactionResponse, TaskMeta>(taskId, taskType, taskMeta);

      const breakdown = EvmUndecodedTransactionResponse.parse(snakeCaseTransformer(result));

      if (Object.keys(breakdown).length > 0) {
        updateUndecodedTransactionsStatus(
          Object.fromEntries(
            Object.entries(breakdown).map(([chain, entry]) => [
              chain,
              // The ws message assumes that total is the number of undecoded txs,
              // For this reason we initialize the status similarly and ignore the total,
              // which in this case is the total of all transactions.
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
        // If the response is empty, it means all chains has been processed.
        // We should set the processed equal to total, so it appears as completed.
        clearUndecodedTransactionsNumbers();
      }
    }
    catch (error: any) {
      if (isTaskCancelled(error))
        return;

      const description = t('actions.history.fetch_undecoded_transactions.error.message', {
        message: error.message,
      });
      notify({
        display: true,
        message: description,
        title,
      });
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
    const taskType = TaskType.TRANSACTIONS_DECODING;

    if (isTaskRunning(taskType, { chain }))
      return;

    try {
      const { taskId } = await decodeTransactions(chain, ignoreCache);

      const taskMeta = {
        all: false,
        chain,
        description: t('actions.transactions_redecode_by_chain.task.description', { chain: get(getChainName(chain)) }),
        title: t('actions.transactions_redecode_by_chain.task.title'),
      };

      await awaitTask(taskId, taskType, taskMeta, true);
      clearDependedSection();
    }
    catch (error) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        notify({
          display: true,
          message: t('actions.transactions_redecode_by_chain.error.description', {
            chain: get(getChainName(chain)),
            error,
          }),
          title: t('actions.transactions_redecode_by_chain.error.title'),
        });
      }
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
      .map(({ chain }) => chain);
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
    const decodeChains = chains.length > 0 ? chains : get(evmAndEvmLikeTxChainsInfo).map(chain => chain.id);

    await awaitParallelExecution(
      decodeChains,
      item => item,
      async item => decodeTransactionsTask(item, true),
      2,
    );
  };

  const pullAndRecodeTransactions = async (payload: PullTransactionPayload): Promise<void> => {
    try {
      const taskType = TaskType.TRANSACTIONS_DECODING;
      const { taskId } = await pullAndRecodeTransactionRequest(payload);

      let taskMeta = {
        description: t('actions.transactions_redecode.task.single_description', {
          chain: get(getChainName(payload.chain)),
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

      const { result } = await awaitTask<boolean, TaskMeta>(taskId, taskType, taskMeta, true);

      if (result)
        clearDependedSection();
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        notify({
          display: true,
          message: t('actions.transactions_redecode.error.description', {
            error,
          }),
          title: t('actions.transactions_redecode.error.title'),
        });
      }
    }
  };

  const pullAndRedecodeTransactions = async ({ deleteCustom, transactions }: PullEvmTransactionPayload): Promise<void> => {
    resetUndecodedTransactionsStatus();

    const grouped = groupBy(transactions, item => item.evmChain);
    Object.entries(grouped).forEach(([chain, transactions]) => {
      updateUndecodedTransactionsStatus({
        [chain]: {
          chain,
          processed: 0,
          total: transactions.length,
        },
      });
    });

    const evmChainsMap = new Map<string, string[]>();
    const evmLikeChainsMap = new Map<string, string[]>();

    transactions.forEach((item) => {
      const chain = getChain(item.evmChain);

      if (isEvmLikeChains(chain)) {
        if (!evmLikeChainsMap.has(chain))
          evmLikeChainsMap.set(chain, []);

        evmLikeChainsMap.get(chain)!.push(item.txHash);
      }
      else {
        if (!evmChainsMap.has(chain))
          evmChainsMap.set(chain, []);

        evmChainsMap.get(chain)!.push(item.txHash);
      }
    });

    if (evmChainsMap.size > 0) {
      await awaitParallelExecution(
        Array.from(evmChainsMap.entries()),
        ([chain]) => chain,
        async ([chain, txRefs]) => pullAndRecodeTransactions({ chain, deleteCustom, txRefs }),
        2,
      );
    }

    if (evmLikeChainsMap.size > 0) {
      await awaitParallelExecution(
        Array.from(evmLikeChainsMap.entries()),
        ([chain]) => chain,
        async ([chain, txRefs]) => pullAndRecodeTransactions({ chain, deleteCustom, txRefs }),
        2,
      );
    }
  };

  const pullAndRecodeEthBlockEvents = async (payload: PullEthBlockEventPayload): Promise<void> => {
    try {
      const taskType = TaskType.ETH_BLOCK_EVENTS_DECODING;
      const { taskId } = await pullAndRecodeEthBlockEventRequest(payload);

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

      const { result } = await awaitTask<boolean, TaskMeta>(taskId, taskType, taskMeta, true);

      if (result)
        clearDependedSection();
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        notify({
          display: true,
          message: t('actions.eth_block_events_redecoding.error.description', {
            error,
          }),
          title: t('actions.eth_block_events_redecoding.error.title'),
        });
      }
    }
  };

  return {
    checkMissingEventsAndRedecode,
    decodeTransactionsTask,
    fetchUndecodedTransactionsBreakdown,
    fetchUndecodedTransactionsStatus,
    pullAndRecodeEthBlockEvents,
    pullAndRedecodeTransactions,
    redecodeTransactions,
  };
});
