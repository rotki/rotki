import { type ActivityId, ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';

/**
 * Members of a targeted set, in an id.
 *
 * Sorted so the same set asked for in a different order is the same run, and comma-joined so
 * `activityParts` recovers the set as one part instead of shredding it into members — the same
 * treatment the chain sweep gives its chain list.
 */
function asScope(members: readonly (string | number)[]): string {
  return Array.from(members, String)
    .sort()
    .join(',');
}

/**
 * The identity of one chain's decode.
 *
 * Shared, never rebuilt at each site: a flow names its children before they exist and the
 * mechanism submits them later, and a divergence does not fail loudly — the children are simply
 * never gated by the parent claiming them.
 *
 * `ignoreCache` is part of the identity. A refresh leaves `tx_decoding:<chain>` PENDING with
 * `ignoreCache: false` for the whole sync window, so keyed by chain alone a forced "Redecode all"
 * during that window joins the pending run, never reaches the backend, and still settles COMPLETE.
 */
export function decodeActivityId(chain: string, ignoreCache = false): ActivityId {
  return makeActivityId(ActivityKind.TX_DECODING, chain, ignoreCache ? ActivityPart.PULL : ActivityPart.CACHED);
}

/**
 * The identity of one chain's decode within a *targeted* request.
 *
 * The tx refs are part of the identity, not decoration. This was
 * `TX_DECODING:<chain>:PULL` — scoped by chain alone — while the activity is `rerunnable: false`
 * and its payload is the request. Two different tx sets on one chain therefore deduped onto each
 * other and the second caller was handed the first run's promise, so its transactions were never
 * decoded.
 */
export function targetedDecodeActivityId(chain: string, txRefs: readonly string[]): ActivityId {
  return makeActivityId(ActivityKind.TX_DECODING, chain, ActivityPart.PULL, asScope(txRefs));
}

/**
 * Builds the activity id identifying a block-event decode.
 *
 * @remarks
 * The block numbers are the request, so they belong in the id even though block events are
 * ethereum-only: one chain is not one request.
 */
export function blockDecodeActivityId(blockNumbers: readonly number[]): ActivityId {
  return makeActivityId(ActivityKind.ETH_BLOCK_DECODING, asScope(blockNumbers));
}
