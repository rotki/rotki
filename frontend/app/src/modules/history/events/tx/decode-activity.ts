import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { DECODE_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { type ActivityId, ActivityKind, ActivityPart } from '@/modules/task-center/core/types';

/**
 * Members of a targeted set, in an id.
 *
 * Sorted so the same set asked for in a different order is the same run, and comma-joined so
 * `activityParts` recovers the set as one part instead of shredding it into members, the same
 * treatment the chain sweep gives its chain list.
 */
function asScope(members: readonly (string | number)[]): string {
  return Array.from(members, String)
    .sort()
    .join(',');
}

/** Whether a decode bypasses the cache, as the id part that distinguishes the two runs. */
function cachePart(ignoreCache: boolean): ActivityPart {
  return ignoreCache ? ActivityPart.PULL : ActivityPart.CACHED;
}

/** One chain's decode, and whether it bypasses the cache. */
export interface DecodeSubject {
  readonly chain: string;
  readonly ignoreCache: boolean;
}

/** One chain's decode of a named set of transactions. */
export interface TargetedDecodeSubject {
  readonly chain: string;
  readonly txRefs: readonly string[];
}

/**
 * One chain's decode.
 *
 * `ignoreCache` is part of the identity. A refresh leaves the cached run PENDING for the whole sync
 * window, so keyed by chain alone a forced "Redecode all" during that window joins the pending run,
 * never reaches the backend, and still settles COMPLETE.
 *
 * No fixed part: `TX_DECODING` hosts one operation, and the cache flag that varies belongs after
 * the chain, so a coarse reader can ask about a chain without knowing which variant ran.
 */
export const decodeActivity = defineActivity<DecodeSubject, readonly [string, ActivityPart]>({
  key: subject => [subject.chain, cachePart(subject.ignoreCache)],
  kind: ActivityKind.TX_DECODING,
  lane: () => DECODE_LANE,
});

/**
 * One chain's decode within a *targeted* request.
 *
 * The tx refs are part of the identity, not decoration. Scoped by chain alone, while the activity
 * is `rerunnable: false` and its payload is the request, two different tx sets on one chain deduped
 * onto each other and the second caller was handed the first run's promise, so its transactions
 * were never decoded.
 */
export const targetedDecodeActivity = defineActivity<TargetedDecodeSubject, readonly [string, ActivityPart, string]>({
  key: subject => [subject.chain, ActivityPart.PULL, asScope(subject.txRefs)],
  kind: ActivityKind.TX_DECODING,
  lane: () => DECODE_LANE,
});

/**
 * A block-event decode.
 *
 * @remarks
 * The block numbers are the request, so they belong in the id even though block events are
 * ethereum-only: one chain is not one request.
 */
export const blockDecodeActivity = defineActivity<{ blockNumbers: readonly number[] }, readonly [string]>({
  key: subject => [asScope(subject.blockNumbers)],
  kind: ActivityKind.ETH_BLOCK_DECODING,
  lane: () => DECODE_LANE,
});

/**
 * The identity of one chain's decode.
 *
 * Delegates to {@link decodeActivity} rather than composing an id of its own, so there is one
 * definition. A flow names its children before they exist and the mechanism submits them later, and
 * a divergence between the two does not fail loudly: the children are simply never gated by the
 * parent claiming them.
 */
export function decodeActivityId(chain: string, ignoreCache = false): ActivityId {
  return decodeActivity.id({ chain, ignoreCache });
}

/** The identity of one chain's decode within a targeted request. See {@link targetedDecodeActivity}. */
export function targetedDecodeActivityId(chain: string, txRefs: readonly string[]): ActivityId {
  return targetedDecodeActivity.id({ chain, txRefs });
}

/** The identity of a block-event decode. See {@link blockDecodeActivity}. */
export function blockDecodeActivityId(blockNumbers: readonly number[]): ActivityId {
  return blockDecodeActivity.id({ blockNumbers });
}
