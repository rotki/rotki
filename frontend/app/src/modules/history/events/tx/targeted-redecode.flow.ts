import type { FlowChild, HistoryFlow } from '@/modules/history/events/flows';
import { msg } from '@/message-key';
import { blockDecodeActivityId, targetedDecodeActivityId } from '@/modules/history/events/tx/decode-activity';
import { type ActivityId, ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';

/**
 * One chain's transactions within a targeted request, already resolved from location to chain.
 *
 * Resolved by the producer, not here: mapping a location to its chain is runtime state, and a
 * declaration that reached for it would stop being data.
 */
interface TargetedChainTransactions {
  readonly chain: string;
  readonly txRefs: readonly string[];
}

/** What a targeted re-decode covers: named transactions, named block events, or both. */
export interface TargetedRedecodeScope {
  readonly byChain: readonly TargetedChainTransactions[];
  readonly blocks: readonly number[];
}

/** What each child is invoked with — one chain's transactions, or the block set. */
export type TargetedRedecodeWork =
  | { readonly type: 'transactions'; readonly chain: string; readonly txRefs: readonly string[] }
  | { readonly type: 'blocks'; readonly blockNumbers: readonly number[] };

/**
 * Re-derive a *named* set of transactions and block events, pulling them from the node first.
 *
 * Distinct from {@link redecodeFlow}, which re-reads what is already stored; this pulls from the node
 * first. That verb boundary is why there are two flows and not one per entry point — row-level
 * re-decode, the dialog, block events, the dev-only re-decode page and conflict resolution are all
 * this same work over a different scope.
 *
 * Reset-bearing unconditionally: customized events are always deleted and regenerated (the
 * confirmation dialog forces `deleteCustom`), and with none present the non-customized events are
 * still deleted and re-derived. So this must never overlap matching, which writes to those rows.
 */
export const targetedRedecodeFlow: HistoryFlow<TargetedRedecodeScope, TargetedRedecodeWork> = {
  /**
   * One decode per chain, plus one for the block set when the request covers any.
   *
   * Heterogeneous on purpose — a targeted request can name transactions, block events or both, and
   * the two are decoded by different backend calls. The ids come from the same constructors the
   * mechanism submits under, so a declared child cannot drift out of its parent's gate.
   */
  children: ({ blocks, byChain }: TargetedRedecodeScope): readonly FlowChild<TargetedRedecodeWork>[] => [
    ...byChain.map(({ chain, txRefs }) => ({
      id: targetedDecodeActivityId(chain, txRefs),
      kind: ActivityKind.TX_DECODING,
      payload: { chain, txRefs, type: 'transactions' } as const,
    })),
    ...(blocks.length > 0
      ? [{
          id: blockDecodeActivityId(blocks),
          kind: ActivityKind.ETH_BLOCK_DECODING,
          payload: { blockNumbers: blocks, type: 'blocks' } as const,
        }]
      : []),
  ],
  /**
   * The request *is* the identity. Members are sorted so the same set asked for in any order is one
   * run, and joined into a single part so `activityParts` recovers the set rather than shredding it.
   *
   * There is no unscoped form. Omitting the scope on the chain sweep means "everything", which
   * is a meaningful request; a targeted re-decode of nothing is not, so an empty scope still yields
   * a distinct id rather than collapsing onto some canonical run.
   */
  id: (scope?: TargetedRedecodeScope): ActivityId => {
    const members = [
      ...(scope?.byChain ?? []).flatMap(({ chain, txRefs }) => txRefs.map(txRef => `${chain}/${txRef}`)),
      ...(scope?.blocks ?? []).map(block => `block/${block}`),
    ];
    return makeActivityId(ActivityKind.REDECODE, ActivityPart.TARGETED, [...members].sort().join(','));
  },
  kind: ActivityKind.REDECODE,
  resets: true,
  titleKey: msg.$t('task_center.group.targeted_redecode'),
};
