import { groupBy } from 'lodash-es';
import { TaskType } from '@/types/task-type';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { Section } from '@/types/status';
import { type ChainAndTxHash, type EvmChainAndTxHash, TransactionChainType } from '@/types/history/events';
import { EvmUndecodedTransactionResponse } from '@/types/websocket-messages';
import type { TaskMeta } from '@/types/task';

export const useHistoryTransactionDecoding = createSharedComposable(() => {
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const { decodeTransactions, getUndecodedTransactionsBreakdown, pullAndRecodeTransactionRequest }
    = useHistoryEventsApi();

  const { awaitTask, isTaskRunning } = useTaskStore();
  const { updateUndecodedTransactionsStatus, getUndecodedTransactionStatus, resetUndecodedTransactionsStatus }
    = useHistoryStore();

  const { txChains, getChain, isEvmLikeChains, getChainName, getEvmChainName } = useSupportedChains();

  const { resetStatus } = useStatusUpdater(Section.HISTORY_EVENT);

  const fetchUndecodedTransactionsBreakdown = async (type: TransactionChainType): Promise<void> => {
    const isEvm = type === TransactionChainType.EVM;
    const taskType = TaskType.FETCH_UNDECODED_TXS;
    if (get(isTaskRunning(taskType, { isEvm }))) {
      logger.debug(`was already fetching undecoded transactions for ${type}`);
      return;
    }

    const title = t('actions.history.fetch_undecoded_transactions.task.title');

    const taskMeta = {
      title,
      isEvm,
    };

    try {
      const { taskId } = await getUndecodedTransactionsBreakdown(type);
      const { result } = await awaitTask<EvmUndecodedTransactionResponse, TaskMeta>(taskId, taskType, taskMeta);

      const breakdown = EvmUndecodedTransactionResponse.parse(snakeCaseTransformer(result));

      updateUndecodedTransactionsStatus(
        Object.fromEntries(
          Object.entries(breakdown).map(([chain, entry]) => [
            chain,
            // The ws message assumes that total is the number of undecoded txs,
            // For this reason we initialize the status similarly and ignore the total,
            // which in this case is the total of all transactions.
            {
              chain,
              total: entry.undecoded,
              processed: 0,
            },
          ]),
        ),
      );
    }
    catch (error: any) {
      if (isTaskCancelled(error))
        return;

      const description = t('actions.history.fetch_undecoded_transactions.error.message', {
        message: error.message,
      });
      notify({
        title,
        message: description,
        display: true,
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

    if (get(isTaskRunning(taskType, { chain })))
      return;

    try {
      const { taskId } = await decodeTransactions([chain], type, ignoreCache);

      const taskMeta = {
        title: t('actions.transactions_redecode_by_chain.task.title'),
        description: t('actions.transactions_redecode_by_chain.task.description', { chain: get(getChainName(chain)) }),
        chain,
        all: false,
      };

      await awaitTask(taskId, taskType, taskMeta, true);
      clearDependedSection();
    }
    catch (error) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        notify({
          title: t('actions.transactions_redecode_by_chain.error.title'),
          message: t('actions.transactions_redecode_by_chain.error.description', {
            error,
            chain: get(getChainName(chain)),
          }),
          display: true,
        });
      }
    }
  };

  const checkMissingEventsAndRedecodeHandler = async (type: TransactionChainType): Promise<void> => {
    const isEvmType = type === TransactionChainType.EVM;
    const chains = getUndecodedTransactionStatus()
      .filter(({ total, processed, chain }) => {
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
            type: TransactionChainType.EVMLIKE,
            chain,
          };
        }

        return {
          type: TransactionChainType.EVM,
          chain: getEvmChainName(chain) || '',
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

  const pullAndRecodeTransactionsByType = async (payload: (ChainAndTxHash | EvmChainAndTxHash)[], type: TransactionChainType): Promise<void> => {
    try {
      const taskType = TaskType.TRANSACTIONS_DECODING;
      const { taskId } = await pullAndRecodeTransactionRequest(payload, type);

      let taskMeta = {
        title: t('actions.transactions_redecode.task.title'),
        description: t('actions.transactions_redecode.task.single_description', {
          number: payload.length,
        }),
      };

      if (payload.length === 1) {
        const data = payload[0];
        taskMeta = {
          title: t('actions.transactions_redecode.task.title'),
          description: t('actions.transactions_redecode.task.description', {
            tx: data.txHash,
            chain: 'chain' in data ? data.chain : getChain(data.evmChain),
          }),
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
          title: t('actions.transactions_redecode.error.title'),
          message: t('actions.transactions_redecode.error.description', {
            error,
          }),
          display: true,
        });
      }
    }
  };

  const pullAndRedecodeTransactions = async (transactions: EvmChainAndTxHash[]): Promise<void> => {
    resetUndecodedTransactionsStatus();

    const groupped = groupBy(transactions, 'evmChain');
    Object.entries(groupped).forEach(([chain, transactions]) => {
      updateUndecodedTransactionsStatus({
        [chain]: {
          chain,
          total: transactions.length,
          processed: 0,
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
            deleteCustom: item.deleteCustom,
          },
        );
      }
      else {
        evmLikeChainsPayload.push(
          {
            chain,
            txHash: item.txHash,
            deleteCustom: item.deleteCustom,
          },
        );
      }
    });

    if (evmChainsPayload.length > 0) {
      await pullAndRecodeTransactionsByType(evmChainsPayload, TransactionChainType.EVM);
    }

    if (evmLikeChainsPayload.length > 0) {
      await pullAndRecodeTransactionsByType(evmLikeChainsPayload, TransactionChainType.EVMLIKE);
    }
  };

  return {
    decodeTransactionsTask,
    checkMissingEventsAndRedecode,
    fetchUndecodedTransactionsBreakdown,
    fetchUndecodedTransactionsStatus,
    pullAndRedecodeTransactions,
    redecodeTransactions,
  };
});
