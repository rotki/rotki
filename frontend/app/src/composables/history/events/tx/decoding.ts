import { groupBy } from 'lodash-es';
import { TaskType } from '@/types/task-type';
import { type PendingTask, type TaskMeta } from '@/types/task';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { Section } from '@/types/status';
import {
  type EvmChainAndTxHash,
  type TransactionHashAndEvmChainPayload
} from '@/types/history/events';
import { type Writeable } from '@/types';

export const useHistoryTransactionDecoding = createSharedComposable(() => {
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const {
    reDecodeMissingTransactionEvents,
    getUnDecodedTransactionEventsBreakdown,
    decodeHistoryEvents
  } = useHistoryEventsApi();

  const { awaitTask, isTaskRunning } = useTaskStore();

  const { txEvmChains } = useSupportedChains();

  const { resetEvmUndecodedTransactionsStatus } = useHistoryStore();

  const { resetStatus } = useStatusUpdater(Section.HISTORY_EVENT);

  const unDecodedEventsBreakdown: Ref<Record<string, number>> = ref({});

  const fetchUndecodedEventsBreakdown = async () => {
    const taskType = TaskType.EVM_UNDECODED_EVENTS;
    if (get(isTaskRunning(taskType))) {
      return;
    }

    const title = t('actions.history.fetch_undecoded_events.task.title');

    try {
      const { taskId } = await getUnDecodedTransactionEventsBreakdown();
      const { result } = await awaitTask<Record<string, number>, TaskMeta>(
        taskId,
        taskType,
        {
          title
        }
      );
      set(unDecodedEventsBreakdown, snakeCaseTransformer(result));
    } catch (e: any) {
      const description = t(
        'actions.history.fetch_undecoded_events.error.message',
        {
          message: e.message
        }
      );

      notify({
        title,
        message: description,
        display: true
      });
    }
  };

  const checkMissingTransactionEventsAndRedecode = async () => {
    resetEvmUndecodedTransactionsStatus();
    const evmChains = Object.entries(get(unDecodedEventsBreakdown))
      .filter(([_, number]) => number > 0)
      .map(([evmChain]) => evmChain);
    await awaitParallelExecution(
      evmChains,
      item => item,
      reDecodeMissingTransactionEventsTask
    );
  };

  const reDecodeMissingTransactionEventsTask = async (evmChain: string) => {
    await fetchUndecodedEventsBreakdown();
    const taskType = TaskType.EVM_EVENTS_DECODING;

    if (get(isTaskRunning(taskType, { evmChain }))) {
      return;
    }

    try {
      const { taskId } = await reDecodeMissingTransactionEvents<PendingTask>([
        evmChain
      ]);

      const taskMeta = {
        title: t('actions.transactions_redecode_missing.task.title'),
        description: t(
          'actions.transactions_redecode_missing.task.description',
          { evmChain }
        ),
        evmChain,
        all: false
      };

      await awaitTask(taskId, taskType, taskMeta, true);
      clearDependedSection();
    } catch (e) {
      logger.error(e);
      notify({
        title: t('actions.transactions_redecode_missing.error.title'),
        message: t('actions.transactions_redecode_missing.error.description', {
          error: e,
          evmChain
        }),
        display: true
      });
    }
  };

  const clearDependedSection = () => {
    resetStatus(Section.DEFI_LIQUITY_STAKING);
    resetStatus(Section.DEFI_LIQUITY_STAKING_POOLS);
    resetStatus(Section.DEFI_LIQUITY_STATISTICS);
  };

  const fetchTransactionEvents = async (
    transactions: EvmChainAndTxHash[] | { evmChain: string }[] | null,
    ignoreCache = false
  ): Promise<void> => {
    const isFetchAll = transactions === null;
    let payloads: TransactionHashAndEvmChainPayload[] = [];

    if (isFetchAll) {
      payloads = get(txEvmChains).map(chain => ({
        evmChain: chain.evmChainName
      }));
    } else {
      if (transactions.length === 0) {
        return;
      }

      payloads = Object.entries(groupBy(transactions, 'evmChain')).map(
        ([evmChain, item]: [
          evmChain: string,
          item: EvmChainAndTxHash[] | { evmChain: string }[]
        ]) => {
          const payload: Writeable<TransactionHashAndEvmChainPayload> = {
            evmChain
          };

          const txHashes = item
            .map(data => ('txHash' in data ? data.txHash : ''))
            .filter(item => !!item);

          if (txHashes.length > 0) {
            payload.txHashes = txHashes;
          }

          return payload;
        }
      );
    }

    resetEvmUndecodedTransactionsStatus();
    try {
      const taskType = TaskType.EVM_EVENTS_DECODING;
      const { taskId } = await decodeHistoryEvents({
        data: payloads,
        ignoreCache
      });
      const taskMeta = {
        title: t('actions.transactions_redecode.task.title'),
        description: t('actions.transactions_redecode.task.description'),
        all: true
      };

      const { result } = await awaitTask<boolean, TaskMeta>(
        taskId,
        taskType,
        taskMeta,
        true
      );

      if (result) {
        clearDependedSection();
      }
    } catch (e: any) {
      logger.error(e);
      notify({
        title: t('actions.transactions_redecode.error.title'),
        message: t('actions.transactions_redecode.error.description', {
          error: e
        }),
        display: true
      });
    }
  };

  return {
    reDecodeMissingTransactionEventsTask,
    checkMissingTransactionEventsAndRedecode,
    unDecodedEventsBreakdown,
    fetchUndecodedEventsBreakdown,
    fetchTransactionEvents
  };
});
