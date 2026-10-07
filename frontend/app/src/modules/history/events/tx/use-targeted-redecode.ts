import type {
  LocationAndTxRef,
  PullEthBlockEventPayload,
  PullLocationTransactionPayload,
  PullTransactionPayload,
} from '@/modules/history/events/event-payloads';
import type { ActivityId } from '@/modules/task-center/core/types';
import { groupBy } from 'es-toolkit';
import { err, flatMap as flatMapResult, isErr, map as mapResult, ok, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { combineSettled, isActionable, onActionableError, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { blockDecodeActivity, targetedDecodeActivity } from '@/modules/history/events/tx/decode-activity';
import { targetedRedecodeFlow, type TargetedRedecodeScope } from '@/modules/history/events/tx/targeted-redecode.flow';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { UMBRELLA_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { useNativeTask } from '@/modules/task-center/use-native-task';

/** What a targeted re-decode is asked for: transactions, block events, or both. */
type TargetedRedecodeRequest = Partial<PullLocationTransactionPayload> & Partial<PullEthBlockEventPayload>;

interface UseTargetedRedecodeReturn {
  pullAndDecodeTransactionsRaw: (payload: PullTransactionPayload, parent?: ActivityId) => Promise<void>;
  redecodeTargeted: (payload: TargetedRedecodeRequest) => Promise<void>;
}

/**
 * Re-decoding a *named* set of transactions or block events, rather than sweeping a chain.
 *
 * Distinct from the chain-wide redecode flow in the one way that matters: the payload is the
 * request, so these are never rerunnable and never dedup against each other. They also pull from
 * the node before decoding, which the chain sweep does not.
 */
export function useTargetedRedecode(): UseTargetedRedecodeReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { pullAndRecodeEthBlockEventRequest, pullAndRecodeTransactionRequest } = useHistoryEventsApi();
  const { submitTask } = useNativeTask();
  const { resetUndecodedTransactionsStatus, updateUndecodedTransactionsStatus } = useDecodingStatusStore();
  const { getChain, getChainName, isEvmLikeChains, isSolanaChains } = useSupportedChains();

  /**
   * Pulls and re-decodes a named set of transactions as one activity.
   *
   * @remarks
   * The backend answers a failed pull or decode with a `false` result rather than an error, so the
   * activity turns that `false` into its own failure: its row ends failed, not done.
   */
  const pullAndDecode = async (payload: PullTransactionPayload, parent?: ActivityId): Promise<Result<void, TaskError>> => {
    const count = payload.txRefs.length;
    const chain = getChainName(payload.chain);
    const subtitle = count === 1
      ? activityLabelFor(msg.$t('task_center.activity.tx_decoding.single'), { chain, tx: truncateAddress(payload.txRefs[0]) })
      : activityLabelFor(msg.$t('task_center.activity.tx_decoding.batch'), { chain, count }, count);

    return submitTask({
      id: targetedDecodeActivity.id(payload),
      kind: targetedDecodeActivity.kind,
      lane: targetedDecodeActivity.laneOf?.(payload),
      parent,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => flatMapResult(
        await runTask<boolean>(
          async () => pullAndRecodeTransactionRequest(payload),
        ),
        decoded => (decoded ? ok(undefined) : err(TaskFailed({ message: t('actions.transactions_redecode.error.not_decoded') }))),
      ),
      subtitle,
      title: t('task_center.group.tx_decoding'),
    });
  };

  /**
   * Pulls and re-decodes a named set of transactions, throwing on failure instead of notifying.
   * For callers that handle their own errors, such as conflict resolution.
   */
  const pullAndDecodeTransactionsRaw = async (payload: PullTransactionPayload, parent?: ActivityId): Promise<void> => {
    const outcome = await pullAndDecode(payload, parent);
    if (isErr(outcome) && isActionable(outcome.error))
      throw new Error(outcome.error.message);
  };

  /**
   * The UI redecode flow: the failure belongs to the activity's dock row, so it is only logged here
   * and handed back for the umbrella to combine.
   */
  const pullAndDecodeTransactions = async (payload: PullTransactionPayload, parent?: ActivityId): Promise<Result<void, TaskError>> => {
    const outcome = await pullAndDecode(payload, parent);
    onActionableError(outcome, error => logger.error(error.message));
    return outcome;
  };

  const decodeBlockEvents = async (blockNumbers: readonly number[], parent?: ActivityId): Promise<Result<void, TaskError>> => {
    const count = blockNumbers.length;
    const subtitle = count === 1
      ? activityLabelFor(msg.$t('task_center.activity.eth_block_decoding.single'), { block: blockNumbers[0] })
      : activityLabelFor(msg.$t('task_center.activity.eth_block_decoding.batch'), { count }, count);

    const outcome = await submitTask({
      id: blockDecodeActivity.id({ blockNumbers }),
      kind: blockDecodeActivity.kind,
      lane: blockDecodeActivity.laneOf?.({ blockNumbers }),
      parent,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => pullAndRecodeEthBlockEventRequest({ blockNumbers: [...blockNumbers] }),
        ),
        () => {},
      ),
      subtitle,
      title: t('task_center.group.eth_block_decoding'),
    });

    onActionableError(outcome, error => logger.error(error.message));
    return outcome;
  };

  /** Group the requested transactions onto their chains — the resolution the declaration cannot do. */
  const resolveScope = (transactions: LocationAndTxRef[], blockNumbers: number[]): TargetedRedecodeScope => {
    const byChain = new Map<string, string[]>();
    for (const item of transactions) {
      const chain = getChain(item.location);
      const refs = byChain.get(chain);
      if (refs)
        refs.push(item.txRef);
      else
        byChain.set(chain, [item.txRef]);
    }

    return {
      blocks: blockNumbers,
      byChain: Array.from(byChain.entries()).map(([chain, txRefs]) => ({ chain, txRefs })),
    };
  };

  /**
   * The user-facing targeted re-decode, as one activity with the per-chain decodes and the block
   * decode as its children.
   *
   * @remarks
   * One umbrella for the whole request, so a page re-decode covering transactions *and* block
   * events is one named flow rather than N anonymous decodes plus a separate block activity. The
   * shape is read off {@link targetedRedecodeFlow} rather than rebuilt, so what a test asserts about
   * the declaration is what runs.
   *
   * The umbrella is submitted before its children so the parent gate applies to them, but its `run`
   * needs their promises, which only exist once submitted; the `subtree` promise bridges the two.
   * Each child resolves to its outcome rather than throwing, so one chain failing marks that child
   * and leaves the others running. The umbrella fails only when no child got through
   * (`combineSettled`), as the chain sweep does.
   */
  const redecodeTargeted = async ({
    blockNumbers = [],
    customIndexersOrder,
    deleteCustom,
    transactions = [],
  }: TargetedRedecodeRequest): Promise<void> => {
    if (transactions.length === 0 && blockNumbers.length === 0)
      return;

    if (transactions.length > 0) {
      resetUndecodedTransactionsStatus();
      const grouped = groupBy(transactions, item => item.location);
      Object.entries(grouped).forEach(([chain, items]) => {
        updateUndecodedTransactionsStatus({ [chain]: { chain, processed: 0, total: items.length } });
      });
    }

    const scope = resolveScope([...transactions], [...blockNumbers]);
    const flowId = targetedRedecodeFlow.id(scope);
    const children = targetedRedecodeFlow.children(scope);
    const isEvm = (chain: string): boolean => !isEvmLikeChains(chain) && !isSolanaChains(chain);

    let declared!: (work: readonly Promise<Result<void, TaskError>>[]) => void;
    const subtree = new Promise<readonly Promise<Result<void, TaskError>>[]>((resolve) => {
      declared = resolve;
    });

    const flow = submitTask({
      id: flowId,
      kind: targetedRedecodeFlow.kind,
      lane: UMBRELLA_LANE,
      rerunnable: false,
      resets: targetedRedecodeFlow.resets,
      userStarted: true,
      run: async (): Promise<Result<void, TaskError>> => combineSettled(await subtree),
      subtitle: children.length === 1
        ? undefined
        : activityLabelFor(msg.$t('task_center.count.transactions'), { count: children.length }, children.length),
      title: t(targetedRedecodeFlow.titleKey),
    });

    declared(children.map(async (child) => {
      if (child.payload.type === 'blocks')
        return decodeBlockEvents(child.payload.blockNumbers, flowId);

      const { chain, txRefs } = child.payload;
      return pullAndDecodeTransactions({
        chain,
        // The chain-type split survives only because `customIndexersOrder` is an EVM-only option.
        customIndexersOrder: isEvm(chain) ? customIndexersOrder : undefined,
        deleteCustom,
        txRefs: [...txRefs],
      }, flowId);
    }));

    await flow;
  };

  return {
    pullAndDecodeTransactionsRaw,
    redecodeTargeted,
  };
}
