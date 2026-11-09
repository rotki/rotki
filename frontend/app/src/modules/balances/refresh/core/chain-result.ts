/** What to do with one chain's balance result. */
export const ChainResultDecision = {
  /** Write the balances. */
  APPLY: 'apply',
  /** Keep the chain's earlier success: this failure says nothing about the rest of the chain. */
  KEEP_EARLIER: 'keep-earlier',
  /** Forget the chain's earlier success: the whole chain could not be read. */
  FORGET_EARLIER: 'forget-earlier',
  /** Refuse the balances: the chain already holds newer ones. */
  REFUSE_OLDER: 'refuse-older',
  /** Ignore the result, whatever it holds: a network result landed after it began. */
  DROP_OVERTAKEN: 'drop-overtaken',
} as const;

export type ChainResultDecision = (typeof ChainResultDecision)[keyof typeof ChainResultDecision];

export interface ChainResultFacts {
  readonly failed: boolean;
  /** The result covers only some of the chain's addresses. */
  readonly isTargeted: boolean;
  /** Its timestamp is older than the one the chain holds. Never true without both timestamps. */
  readonly olderThanStored: boolean;
  /** A network result was applied to the chain while this result was in flight. */
  readonly overtaken: boolean;
}

/**
 * Decides what one chain's balance result does to the chain.
 *
 * @remarks
 * Overtaken comes first because it is the only check that holds for a failure too: a read that
 * failed after a network result landed must not forget that result. It also has to precede the
 * timestamp check, which cannot see it. The backend reads the timestamp after the balances, so an
 * overtaken read can carry the newer query's timestamp, or none at all after an account change.
 *
 * A tie is not refused, because a deliberate re-read (a threshold change, an un-ignored asset) has
 * the same timestamp and different content.
 */
export function decideChainResult({ failed, isTargeted, olderThanStored, overtaken }: ChainResultFacts): ChainResultDecision {
  if (overtaken)
    return ChainResultDecision.DROP_OVERTAKEN;
  if (failed)
    return isTargeted ? ChainResultDecision.KEEP_EARLIER : ChainResultDecision.FORGET_EARLIER;
  return olderThanStored ? ChainResultDecision.REFUSE_OLDER : ChainResultDecision.APPLY;
}
