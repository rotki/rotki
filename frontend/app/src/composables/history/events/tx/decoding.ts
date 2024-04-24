import { groupBy } from 'lodash-es';
import { TaskType } from '@/types/task-type';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { Section } from '@/types/status';
import {
  type EvmChainAndTxHash,
  TransactionChainType,
  type TransactionHashAndEvmChainPayload,
} from '@/types/history/events';
import { EvmUndecodedTransactionResponse } from '@/types/websocket-messages';
import type { TaskMeta } from '@/types/task';
import type { Writeable } from '@/types';

export const useHistoryTransactionDecoding = createSharedComposable(() => {
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const {
    decodeTransactions,
    getUndecodedTransactionsBreakdown,
    decodeHistoryEvents,
  } = useHistoryEventsApi();

  const { awaitTask, isTaskRunning } = useTaskStore();
  const {
    updateUndecodedTransactionsStatus,
    getUndecodedTransactionStatus,
    resetUndecodedTransactionsStatus,
  } = useHistoryStore();

  const {
    txEvmChains,
    evmLikeChainsData,
    getChain,
    isEvmLikeChains,
    getChainName,
  } = useSupportedChains();

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
      const { result } = await awaitTask<EvmUndecodedTransactionResponse, TaskMeta>(
        taskId,
        taskType,
        taskMeta,
      );

      const breakdown = EvmUndecodedTransactionResponse.parse(snakeCaseTransformer(result));

      updateUndecodedTransactionsStatus(
        Object.fromEntries(Object.entries(breakdown).map(([chain, entry]) => [chain, {
          evmChain: chain,
          total: entry.total,
          processed: entry.total - entry.undecoded,
        }])),
      );
    }
    catch (error: any) {
      if (isTaskCancelled(error))
        return;

      const description = t(
        'actions.history.fetch_undecoded_transactions.error.message',
        {
          message: error.message,
        },
      );
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

  const clearDependedSection = () => {
    resetStatus({ section: Section.DEFI_LIQUITY_STAKING });
    resetStatus({ section: Section.DEFI_LIQUITY_STAKING_POOLS });
    resetStatus({ section: Section.DEFI_LIQUITY_STATISTICS });
  };

  const decodeTransactionsTask = async (chain: string, type: TransactionChainType = TransactionChainType.EVM) => {
    const taskType = TaskType.TRANSACTIONS_DECODING;

    if (get(isTaskRunning(taskType, { chain })))
      return;

    try {
      const { taskId } = await decodeTransactions([chain], type);

      const taskMeta = {
        title: t('actions.transactions_redecode_missing.task.title'),
        description: t(
          'actions.transactions_redecode_missing.task.description',
          { chain: get(getChainName(chain)) },
        ),
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
          title: t('actions.transactions_redecode_missing.error.title'),
          message: t(
            'actions.transactions_redecode_missing.error.description',
            {
              error,
              chain: get(getChainName(chain)),
            },
          ),
          display: true,
        });
      }
    }
  };

  const checkMissingEventsAndRedecodeHandler = async (type: TransactionChainType) => {
    const isEvmType = type === TransactionChainType.EVM;
    const chains = getUndecodedTransactionStatus()
      .filter(({ total, processed, evmChain }) => {
        const chain = getChain(evmChain);
        const isEvmLike = isEvmLikeChains(chain);
        return processed < total && (isEvmType === !isEvmLike);
      })
      .map(({ evmChain }) => evmChain);
    await awaitParallelExecution(
      chains,
      item => item,
      item => decodeTransactionsTask(item, type),
      2,
    );
  };

  const checkMissingEventsAndRedecode = async () => {
    resetUndecodedTransactionsStatus();
    await fetchUndecodedTransactionsStatus();
    await Promise.allSettled([
      checkMissingEventsAndRedecodeHandler(TransactionChainType.EVM),
      checkMissingEventsAndRedecodeHandler(TransactionChainType.EVMLIKE),
    ]);
  };

  const fetchTransactionEvents = async (
    ignoreCache: boolean,
    type: TransactionChainType = TransactionChainType.EVM,
    transactions?: EvmChainAndTxHash[] | { evmChain: string }[],
  ): Promise<void> => {
    const isFetchAll = !transactions;
    let payloads: TransactionHashAndEvmChainPayload[] = [];
    const isEvm = type === TransactionChainType.EVM;

    if (isFetchAll) {
      if (isEvm) {
        payloads = get(txEvmChains).map(chain => ({
          evmChain: chain.evmChainName,
        }));
      }
      else {
        payloads = get(evmLikeChainsData).map(chain => ({
          evmChain: chain.id,
        }));
      }
    }
    else {
      if (transactions.length === 0)
        return;

      payloads = Object.entries(groupBy(transactions, 'evmChain')).map(
        ([evmChain, item]: [
          evmChain: string,
          item: EvmChainAndTxHash[] | { evmChain: string }[],
        ]) => {
          const payload: Writeable<TransactionHashAndEvmChainPayload> = {
            evmChain,
          };

          const txHashes = item
            .map(data => ('txHash' in data ? data.txHash : ''))
            .filter(item => !!item);

          if (txHashes.length > 0)
            payload.txHashes = txHashes;

          return payload;
        },
      );
    }

    resetUndecodedTransactionsStatus();
    try {
      const taskType = TaskType.TRANSACTIONS_DECODING;
      const { taskId } = await decodeHistoryEvents({
        data: payloads,
        ignoreCache,
      }, type);

      const taskMeta = {
        title: t('actions.transactions_redecode.task.title'),
        description: t('actions.transactions_redecode.task.description'),
        all: true,
      };

      const { result } = await awaitTask<boolean, TaskMeta>(
        taskId,
        taskType,
        taskMeta,
        true,
      );

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

  return {
    decodeTransactionsTask,
    checkMissingEventsAndRedecode,
    fetchUndecodedTransactionsBreakdown,
    fetchUndecodedTransactionsStatus,
    fetchTransactionEvents,
  };
});
