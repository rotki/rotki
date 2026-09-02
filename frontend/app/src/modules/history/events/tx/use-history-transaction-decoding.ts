import { isErr, map as mapResult, ok, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, isCancellation, type TaskError } from '@/modules/core/tasks/task-result';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import {
  TransactionChainType,
  TransactionChainTypeNeedDecoding,
} from '@/modules/history/events/event-payloads';
import { decodeActivityId } from '@/modules/history/events/tx/decode-activity';
import { redecodeFlow } from '@/modules/history/events/tx/redecode.flow';
import { useUndecodedTransactionsStatus } from '@/modules/history/events/tx/use-undecoded-transactions-status';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { DECODE_LANE, UMBRELLA_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { type ActivityId, ActivityKind } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

/**
 * Where a decode sits in a pre-declared tree: which syncs must finish before it may start, whose
 * child it is, and when it has nothing to do. Absent for the imperative re-decode entry points,
 * which submit a decode on its own and run it straight away.
 */
export interface DecodePlacement {
  readonly deps?: readonly ActivityId[];
  readonly parent?: ActivityId;
  readonly skipWhen?: () => boolean;
}

/**
 * Decoding a chain's transactions: the per-chain mechanism, and the flow that runs it over a set.
 *
 * Deliberately not everything decode-shaped. Re-decoding a *named* set of transactions or block
 * events lives in `useTargetedRedecode` (payload-specific, never rerunnable, pulls before
 * decoding), and the undecoded counts these consult live in `useUndecodedTransactionsStatus`.
 */
export const useHistoryTransactionDecoding = createSharedComposable(() => {
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();

  const { decodeTransactions } = useHistoryEventsApi();
  const { cancelByKind, submitTask } = useNativeTask();
  const { getUndecodedTransactionStatus, markDecodingCancelled, resetUndecodedTransactionsStatus } = useDecodingStatusStore();
  const { decodableTxChainsInfo, getChainName, isBtcChains, isEvmLikeChains } = useSupportedChains();
  const { fetchUndecodedTransactionsBreakdown } = useUndecodedTransactionsStatus();

  const decodeTransactionsTask = async (
    chain: string,
    ignoreCache = false,
    placement: DecodePlacement = {},
  ): Promise<void> => {
    // One activity per chain, so liveness, cancellation and rerun are all per-chain.
    const outcome = await submitTask({
      deps: placement.deps,
      id: decodeActivityId(chain, ignoreCache),
      kind: ActivityKind.TX_DECODING,
      lane: DECODE_LANE,
      parent: placement.parent,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => {
        if (placement.skipWhen?.())
          return ok(undefined);

        return mapResult(
          await runTask<boolean>(
            async () => decodeTransactions(chain, ignoreCache),
          ),
          () => {},
        );
      },
      subtitle: activityLabelFor(msg.$t('task_center.activity.tx_decoding.chain'), { chain: getChainName(chain) }),
      title: t('task_center.group.tx_decoding'),
    });

    if (isErr(outcome)) {
      const { error } = outcome;
      if (isCancellation(error)) {
        markDecodingCancelled(chain);
      }
      else if (isActionable(error)) {
        logger.error(error.message);
        notifyError(
          t('actions.transactions_redecode_by_chain.error.title'),
          t('actions.transactions_redecode_by_chain.error.description', {
            chain: getChainName(chain),
            error: error.message,
          }),
        );
      }
    }
  };

  const checkMissingEventsAndRedecodeHandler = async (type: TransactionChainType): Promise<void> => {
    const isEvmType = type === TransactionChainType.EVM;
    const chains = getUndecodedTransactionStatus()
      .filter(({ chain, processed, total }) =>
        processed < total && !isBtcChains(chain) && isEvmType === !isEvmLikeChains(chain),
      )
      .map(({ chain }) => chain);
    // Unbounded on purpose: DECODE_LANE is what caps how many chains decode at once.
    await Promise.all(chains.map(async chain => decodeTransactionsTask(chain)));
  };

  const checkMissingEventsAndRedecode = async (): Promise<void> => {
    resetUndecodedTransactionsStatus();
    await fetchUndecodedTransactionsBreakdown();
    await Promise.allSettled(TransactionChainTypeNeedDecoding.map(async item => checkMissingEventsAndRedecodeHandler(item)));
  };

  /**
   * The user-facing re-decode flow, as one activity with the per-chain decodes as its children. The
   * umbrella is what the task center names and what dedups re-entry; the chains are what actually
   * run, bounded by {@link DECODE_LANE}.
   *
   * This resolves the scope and then reads the shape off {@link redecodeFlow} rather than rebuilding
   * it, so what a test asserts about the declaration is what runs. The id carries the scope: a
   * scoped request identifying itself as the full run would be deduped onto a concurrent
   * redecode-all and silently handed that broader run's promise. A request naming every decodable
   * chain *is* the full run, so it takes the canonical id and dedups deliberately.
   */
  const redecodeTransactions = async (chains: string[] = []): Promise<void> => {
    const allChains = get(decodableTxChainsInfo).map(chain => chain.id);
    const decodeChains = chains.length > 0 ? chains : allChains;
    const coversEverything = allChains.every(chain => decodeChains.includes(chain));
    const flowId = redecodeFlow.id(coversEverything ? undefined : decodeChains);
    const children = redecodeFlow.children(decodeChains);

    // The flow is submitted before its children, so its `run` awaits this rather than a still-empty array.
    let declared!: (work: readonly Promise<void>[]) => void;
    const subtree = new Promise<readonly Promise<void>[]>((resolve) => {
      declared = resolve;
    });

    const flow = submitTask({
      id: flowId,
      kind: redecodeFlow.kind,
      lane: UMBRELLA_LANE,
      rerunnable: false,
      resets: redecodeFlow.resets,
      run: async (): Promise<Result<void, TaskError>> => {
        const outcomes = await Promise.allSettled(await subtree);
        const failed = outcomes.filter(outcome => outcome.status === 'rejected').length;

        if (failed > 0)
          logger.debug(`redecode finished with ${failed} of ${outcomes.length} chains failed`);

        return ok(undefined);
      },
      // Only the subtitle carries the scope, so a partial run does not read as the full one.
      subtitle: coversEverything
        ? undefined
        : activityLabelFor(msg.$t('task_center.activity.redecode.chains'), { chains: decodeChains.map(chain => getChainName(chain)).join(', ') }),
      title: t(redecodeFlow.titleKey),
    });

    declared(children.map(async child => decodeTransactionsTask(child.payload, true, { parent: flowId })));

    await flow;
  };

  /**
   * Cancels every decode in flight, whatever submitted it.
   *
   * @remarks
   * Decoding runs under two id shapes at once, `tx_decoding:&lt;chain&gt;` for a chain sweep and
   * `tx_decoding:&lt;chain&gt;:pull` for a targeted re-decode, so cancelling by id would leave the
   * other shape running.
   */
  function cancelDecoding(): void {
    cancelByKind(ActivityKind.TX_DECODING);
  }

  return {
    cancelDecoding,
    checkMissingEventsAndRedecode,
    decodeTransactionsTask,
    // Re-exported because a decode is always preceded by a read of what is left to decode.
    fetchUndecodedTransactionsBreakdown,
    redecodeTransactions,
  };
});
