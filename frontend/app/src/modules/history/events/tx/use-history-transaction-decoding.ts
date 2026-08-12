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
    // One native TX_DECODING activity per chain; the orchestrator owns liveness
    // (`useWorkStatus(ActivityKind.TX_DECODING)`), cancellation and per-chain re-run.
    const outcome = await submitTask({
      deps: placement.deps,
      id: decodeActivityId(chain, ignoreCache),
      kind: ActivityKind.TX_DECODING,
      lane: DECODE_LANE,
      parent: placement.parent,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => {
        // Declared up front alongside the syncs it waits on, so the shape of a refresh does not
        // depend on what the data turns out to be. When there is nothing left to decode it
        // completes without calling the backend, rather than never appearing.
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
    // The store already keys on the canonical chain id, so no resolution is needed here.
    //
    // ⚠️ The evmlike test alone splits the world in two, so anything that is not evmlike counts as
    // EVM. Bitcoin decodes through its own backend path and must not be handed to the EVM decode
    // endpoint — it reaches this store as soon as it reports decoding progress over the websocket.
    const chains = getUndecodedTransactionStatus()
      .filter(({ chain, processed, total }) =>
        processed < total && !isBtcChains(chain) && isEvmType === !isEvmLikeChains(chain),
      )
      .map(({ chain }) => chain);
    // No wrapper: each of these submits onto DECODE_LANE, which is what bounds how many chains
    // decode at once. Wrapping them in a second limiter only hid that.
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
   * it, so what a test asserts about the declaration is what runs. ⚠️ The id carries the scope: a
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

    // The flow is submitted before its children so the parent gate applies to them, but its `run`
    // needs their promises — which only exist once submitted. It waits on this rather than on an
    // array that would still be empty when the run body first executes.
    let declared!: (work: readonly Promise<void>[]) => void;
    const subtree = new Promise<readonly Promise<void>[]>((resolve) => {
      declared = resolve;
    });

    const flow = submitTask({
      id: flowId,
      kind: redecodeFlow.kind,
      lane: UMBRELLA_LANE,
      rerunnable: false,
      // Declared, not hardcoded: the flow is what knows it deletes before re-deriving, and the
      // eligibility rules are what act on it by holding matching off the same rows.
      resets: redecodeFlow.resets,
      run: async (): Promise<Result<void, TaskError>> => {
        // allSettled, never all: one chain failing must not abandon the others.
        //
        // The flow settles COMPLETE even when chains failed. A failure marks the child, never the
        // parent: to an observer the flow did run to completion, and the chain that failed carries
        // its own FAILED status and keeps its stale freshness, so a later run retries exactly that
        // chain and leaves the ones that succeeded alone. Failing the umbrella instead would say
        // the whole re-decode did not happen, and would leave nothing able to distinguish the
        // chains that need retrying from the ones that do not.
        const outcomes = await Promise.allSettled(await subtree);
        const failed = outcomes.filter(outcome => outcome.status === 'rejected').length;

        if (failed > 0)
          logger.debug(`redecode finished with ${failed} of ${outcomes.length} chains failed`);

        return ok(undefined);
      },
      // The title names the flow; the scope only shows up as a subtitle, so a two-chain run is not
      // presented identically to the full one.
      subtitle: coversEverything
        ? undefined
        : activityLabelFor(msg.$t('task_center.activity.redecode.chains'), { chains: decodeChains.map(chain => getChainName(chain)).join(', ') }),
      title: t(redecodeFlow.titleKey),
    });

    declared(children.map(async child => decodeTransactionsTask(child.payload, true, { parent: flowId })));

    await flow;
  };

  // Decoding submits under two id shapes at once (`tx_decoding:<chain>` for a chain sweep,
  // `tx_decoding:<chain>:pull` for a targeted re-decode), so this cancels the whole kind.
  function cancelDecoding(): void {
    cancelByKind(ActivityKind.TX_DECODING);
  }

  return {
    cancelDecoding,
    checkMissingEventsAndRedecode,
    decodeTransactionsTask,
    // Re-exported, not owned: a decode is always preceded by reading what is left to decode, so
    // callers that drive one need both. Consumers that only want the counts take
    // `useUndecodedTransactionsStatus` directly.
    fetchUndecodedTransactionsBreakdown,
    redecodeTransactions,
  };
});
