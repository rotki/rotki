import type { TaskMeta } from '@/types/task';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useSupportedChains } from '@/composables/info/chains';
import { useStatusUpdater } from '@/composables/status';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { useHistoryStore } from '@/store/history';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import {
  type ChainAndTxHash,
  type EvmChainAndTxHash,
  type PullEvmTransactionPayload,
  type PullTransactionPayload,
  TransactionChainType,
} from '@/types/history/events';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { EvmUndecodedTransactionResponse } from '@/types/websocket-messages';
import { isTaskCancelled } from '@/utils';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { logger } from '@/utils/logging';
import { groupBy } from 'es-toolkit';

export const useHistoryTransactionDecoding = createSharedComposable(() => {
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const { decodeTransactions, getUndecodedTransactionsBreakdown, pullAndRecodeTransactionRequest }
    = useHistoryEventsApi();

  const { awaitTask, isTaskRunning } = useTaskStore();
  const {
    clearUndecodedTransactionsNumbers,
    getUndecodedTransactionStatus,
    resetUndecodedTransactionsStatus,
    updateUndecodedTransactionsStatus,
  } = useHistoryStore();

  const { getChain, getChainName, getEvmChainName, isEvmLikeChains, txChains } = useSupportedChains();

  const { resetStatus } = useStatusUpdater(Section.HISTORY);

  const fetchUndecodedTransactionsBreakdown = async (type: TransactionChainType): Promise<void> => {
    const isEvm = type === TransactionChainType.EVM;
    const taskType = TaskType.FETCH_UNDECODED_TXS;
    if (isTaskRunning(taskType, { isEvm })) {
      logger.debug(`was already fetching undecoded transactions for ${type}`);
      return;
    }

    const title = t('actions.history.fetch_undecoded_transactions.task.title');

    const taskMeta = {
      isEvm,
      title,
    };

    try {
      const { taskId } = await getUndecodedTransactionsBreakdown(type);
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
        clearUndecodedTransactionsNumbers(type);
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
    await fetchUndecodedTransactionsBreakdown(TransactionChainType.EVM);
    await fetchUndecodedTransactionsBreakdown(TransactionChainType.EVMLIKE);
  };

  const clearDependedSection = (): void => {
    resetStatus({ section: Section.DEFI_LIQUITY_STAKING });
    resetStatus({ section: Section.DEFI_LIQUITY_STAKING_POOLS });
    resetStatus({ section: Section.DEFI_LIQUITY_STATISTICS });
  };

  const decodeTransactionsTask = async (
    chain: string,
    type: TransactionChainType = TransactionChainType.EVM,
    ignoreCache = false,
  ): Promise<void> => {
    const taskType = TaskType.TRANSACTIONS_DECODING;

    if (isTaskRunning(taskType, { chain }))
      return;

    try {
      const { taskId } = await decodeTransactions([chain], type, ignoreCache);

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
      async item => decodeTransactionsTask(item, type),
      2,
    );
  };

  const checkMissingEventsAndRedecode = async (): Promise<void> => {
    resetUndecodedTransactionsStatus();
    await fetchUndecodedTransactionsStatus();
    await Promise.allSettled([
      checkMissingEventsAndRedecodeHandler(TransactionChainType.EVM),
      checkMissingEventsAndRedecodeHandler(TransactionChainType.EVMLIKE),
    ]);
  };

  const redecodeTransactions = async (chains: string[] = []): Promise<void> => {
    const decodeChains = chains.length > 0 ? chains : get(txChains).map(chain => chain.id);

    const chainInfo = decodeChains
      .map((chain) => {
        if (isEvmLikeChains(chain)) {
          return {
            chain,
            type: TransactionChainType.EVMLIKE,
          };
        }

        return {
          chain: getEvmChainName(chain) || '',
          type: TransactionChainType.EVM,
        };
      })
      .filter(item => item.chain);

    await awaitParallelExecution(
      chainInfo,
      item => item.chain,
      async item => decodeTransactionsTask(item.chain, item.type, true),
      2,
    );
  };

  const pullAndRecodeTransactionsByType = async (payload: PullTransactionPayload, type: TransactionChainType): Promise<void> => {
    try {
      const taskType = TaskType.TRANSACTIONS_DECODING;
      const { taskId } = await pullAndRecodeTransactionRequest(payload, type);

      let taskMeta = {
        description: t('actions.transactions_redecode.task.single_description', {
          number: payload.transactions.length,
        }),
        title: t('actions.transactions_redecode.task.title'),
      };

      if (payload.transactions.length === 1) {
        const data = payload.transactions[0];
        taskMeta = {
          description: t('actions.transactions_redecode.task.description', {
            chain: 'chain' in data ? data.chain : getChain(data.evmChain),
            tx: data.txHash,
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

    const evmChainsPayload: EvmChainAndTxHash[] = [];
    const evmLikeChainsPayload: ChainAndTxHash[] = [];

    transactions.forEach((item) => {
      const chain = getChain(item.evmChain);
      const type = isEvmLikeChains(chain) ? TransactionChainType.EVMLIKE : TransactionChainType.EVM;

      if (type === TransactionChainType.EVM) {
        evmChainsPayload.push(
          {
            evmChain: item.evmChain,
            txHash: item.txHash,
          },
        );
      }
      else {
        evmLikeChainsPayload.push(
          {
            chain,
            txHash: item.txHash,
          },
        );
      }
    });

    if (evmChainsPayload.length > 0) {
      await pullAndRecodeTransactionsByType({ deleteCustom, transactions: evmChainsPayload }, TransactionChainType.EVM);
    }

    if (evmLikeChainsPayload.length > 0) {
      await pullAndRecodeTransactionsByType({ deleteCustom, transactions: evmLikeChainsPayload }, TransactionChainType.EVMLIKE);
    }
  };

  return {
    checkMissingEventsAndRedecode,
    decodeTransactionsTask,
    fetchUndecodedTransactionsBreakdown,
    fetchUndecodedTransactionsStatus,
    pullAndRedecodeTransactions,
    redecodeTransactions,
  };
});
