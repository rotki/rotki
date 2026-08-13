import type {
  LocationAndTxRef,
  PullEthBlockEventPayload,
  PullLocationTransactionPayload,
  PullTransactionPayload,
} from '@/modules/history/events/event-payloads';
import { groupBy } from 'es-toolkit';
import { isErr, map as mapResult, ok, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { blockDecodeActivityId, targetedDecodeActivityId } from '@/modules/history/events/tx/decode-activity';
import { targetedRedecodeFlow, type TargetedRedecodeScope } from '@/modules/history/events/tx/targeted-redecode.flow';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { DECODE_LANE, UMBRELLA_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { type ActivityId, ActivityKind } from '@/modules/task-center/core/types';
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
  const { notifyError } = useNotifications();
  const { pullAndRecodeEthBlockEventRequest, pullAndRecodeTransactionRequest } = useHistoryEventsApi();
  const { submitTask } = useNativeTask();
  const { resetUndecodedTransactionsStatus, updateUndecodedTransactionsStatus } = useDecodingStatusStore();
  const { getChain, getChainName, isEvmLikeChains, isSolanaChains } = useSupportedChains();

  /**
   * Core decode function that throws on failure instead of notifying.
   * Used by callers that need to handle errors themselves (e.g. conflict resolution).
   */
  const pullAndDecodeTransactionsRaw = async (payload: PullTransactionPayload, parent?: ActivityId): Promise<void> => {
    // One tx names itself — truncated, since a full hash does not fit the row; a batch is only
    // meaningful as a count.
    const count = payload.txRefs.length;
    const chain = getChainName(payload.chain);
    const subtitle = count === 1
      ? activityLabelFor(msg.$t('task_center.activity.tx_decoding.single'), { chain, tx: truncateAddress(payload.txRefs[0]) })
      : activityLabelFor(msg.$t('task_center.activity.tx_decoding.batch'), { chain, count }, count);

    // Targeted re-decode of specific tx refs: a one-shot native TX_DECODING activity (not
    // rerunnable — the payload is request-specific). `decoded` carries whether the backend
    // actually re-decoded so the throw-on-no-change contract below is preserved.
    const outcome = await submitTask<boolean>({
      id: targetedDecodeActivityId(payload.chain, payload.txRefs),
      kind: ActivityKind.TX_DECODING,
      lane: DECODE_LANE,
      parent,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<boolean, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => pullAndRecodeTransactionRequest(payload),
        ),
        result => result,
      ),
      subtitle,
      title: t('task_center.group.tx_decoding'),
    });

    if (isErr(outcome)) {
      if (isActionable(outcome.error))
        throw new Error(outcome.error.message);
      return;
    }

    if (!outcome.value)
      throw new Error(t('actions.transactions_redecode.error.title'));
  };

  /**
   * Notifying wrapper — catches errors and shows notifications to the user.
   * Used by the UI redecode flow where errors are displayed as toast messages.
   */
  const pullAndDecodeTransactions = async (payload: PullTransactionPayload, parent?: ActivityId): Promise<void> => {
    try {
      await pullAndDecodeTransactionsRaw(payload, parent);
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

  const decodeBlockEvents = async (blockNumbers: readonly number[], parent?: ActivityId): Promise<void> => {
    const count = blockNumbers.length;
    const subtitle = count === 1
      ? activityLabelFor(msg.$t('task_center.activity.eth_block_decoding.single'), { block: blockNumbers[0] })
      : activityLabelFor(msg.$t('task_center.activity.eth_block_decoding.batch'), { count }, count);

    const outcome = await submitTask({
      id: blockDecodeActivityId(blockNumbers),
      kind: ActivityKind.ETH_BLOCK_DECODING,
      lane: DECODE_LANE,
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

    if (isErr(outcome) && isActionable(outcome.error)) {
      logger.error(outcome.error.message);
      notifyError(
        t('actions.eth_block_events_redecoding.error.title'),
        t('actions.eth_block_events_redecoding.error.description', {
          error: outcome.error.message,
        }),
      );
    }
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
   * One umbrella for the whole request, so a page re-decode covering transactions *and* block
   * events is one named flow rather than N anonymous decodes plus a separate block activity. The
   * shape is read off {@link targetedRedecodeFlow} rather than rebuilt, so what a test asserts about
   * the declaration is what runs.
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

    // The flow is submitted before its children so the parent gate applies to them, but its `run`
    // needs their promises — which only exist once submitted. Same handshake as the chain sweep.
    let declared!: (work: readonly Promise<void>[]) => void;
    const subtree = new Promise<readonly Promise<void>[]>((resolve) => {
      declared = resolve;
    });

    const flow = submitTask({
      id: flowId,
      kind: targetedRedecodeFlow.kind,
      lane: UMBRELLA_LANE,
      rerunnable: false,
      resets: targetedRedecodeFlow.resets,
      run: async (): Promise<Result<void, TaskError>> => {
        // allSettled, never all: one chain failing must not abandon the others. A failure marks the
        // child and leaves the umbrella complete, as it does for the chain sweep.
        await Promise.allSettled(await subtree);
        return ok(undefined);
      },
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
