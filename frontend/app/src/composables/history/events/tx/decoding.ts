import { groupBy } from 'lodash-es';
import { TaskType } from '@/types/task-type';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { Section } from '@/types/status';
import {
  type EvmChainAndTxHash,
  TransactionChainType,
  type TransactionHashAndEvmChainPayload,
} from '@/types/history/events';
import type { TaskMeta } from '@/types/task';
import type { Writeable } from '@/types';

export const useHistoryTransactionDecoding = createSharedComposable(() => {
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const {
    reDecodeMissingEvents,
    getUnDecodedEventsBreakdown,
    decodeHistoryEvents,
  } = useHistoryEventsApi();

  const { awaitTask, isTaskRunning } = useTaskStore();

  const { txEvmChains, evmLikeChainsData } = useSupportedChains();

  const { resetUnDecodedTransactionsStatus } = useHistoryStore();

  const { resetStatus } = useStatusUpdater(Section.HISTORY_EVENT);

  const unDecodedEventsBreakdown: Ref<Record<string, number>> = ref({});

  const fetchUnDecodedEventsBreakdown = async (type: TransactionChainType) => {
    const isEvm = type === TransactionChainType.EVM;
    const taskType = TaskType.FETCH_UNDECODED_EVENTS;
    if (get(isTaskRunning(taskType, { isEvm })))
      return;

    const title = t('actions.history.fetch_undecoded_events.task.title');

    const taskMeta = {
      title,
      isEvm,
    };

    try {
      const { taskId } = await getUnDecodedEventsBreakdown(type);
      const { result } = await awaitTask<Record<string, number>, TaskMeta>(
        taskId,
        taskType,
        taskMeta,
      );
      set(unDecodedEventsBreakdown, {
        ...get(unDecodedEventsBreakdown),
        ...snakeCaseTransformer(result),
      });
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        const description = t(
          'actions.history.fetch_undecoded_events.error.message',
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
    }
  };

  const reDecodeMissingEventsTask = async (chain: string, type: TransactionChainType = TransactionChainType.EVM) => {
    await fetchUnDecodedEventsBreakdown(type);
    const isEvm = type === TransactionChainType.EVM;
    const taskType = TaskType.EVENTS_ENCODING;

    if (get(isTaskRunning(taskType, { chain, isEvm })))
      return;

    try {
      const { taskId } = await reDecodeMissingEvents([
        chain,
      ], type);

      const taskMeta = {
        title: t('actions.transactions_redecode_missing.task.title'),
        description: t(
          'actions.transactions_redecode_missing.task.description',
          { chain },
        ),
        chain,
        all: false,
        isEvm,
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
              chain,
            },
          ),
          display: true,
        });
      }
    }
  };

  const { getChain, isEvmLikeChains } = useSupportedChains();

  const checkMissingEventsAndReDecodeHandler = async (type: TransactionChainType) => {
    const isEvmType = type === TransactionChainType.EVM;
    const chains = Object.entries(get(unDecodedEventsBreakdown))
      .filter(([evmChain, number]) => {
        const chain = getChain(evmChain);
        const isEvmLike = isEvmLikeChains(chain);
        return number > 0 && (isEvmType === !isEvmLike);
      })
      .map(([chain]) => chain);
    await awaitParallelExecution(
      chains,
      item => item,
      item => reDecodeMissingEventsTask(item, type),
    );
  };

  const checkMissingEventsAndReDecode = () => {
    resetUnDecodedTransactionsStatus();
    startPromise(Promise.allSettled([
      checkMissingEventsAndReDecodeHandler(TransactionChainType.EVM),
      checkMissingEventsAndReDecodeHandler(TransactionChainType.EVMLIKE),
    ]));
  };

  const clearDependedSection = () => {
    resetStatus({ section: Section.DEFI_LIQUITY_STAKING });
    resetStatus({ section: Section.DEFI_LIQUITY_STAKING_POOLS });
    resetStatus({ section: Section.DEFI_LIQUITY_STATISTICS });
  };

  const fetchTransactionEvents = async (
    transactions: EvmChainAndTxHash[] | { evmChain: string }[] | null,
    ignoreCache: boolean,
    type: TransactionChainType = TransactionChainType.EVM,
  ): Promise<void> => {
    const isFetchAll = transactions === null;
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

    resetUnDecodedTransactionsStatus();
    try {
      const taskType = TaskType.EVENTS_ENCODING;
      const { taskId } = await decodeHistoryEvents({
        data: payloads,
        ignoreCache,
      }, type);

      const taskMeta = {
        title: t('actions.transactions_redecode.task.title'),
        description: t('actions.transactions_redecode.task.description'),
        all: true,
        isEvm,
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
    reDecodeMissingEventsTask,
    checkMissingEventsAndReDecode,
    unDecodedEventsBreakdown,
    fetchUnDecodedEventsBreakdown,
    fetchTransactionEvents,
  };
});
