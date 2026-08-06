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
 * Shared rather than rebuilt at each site: a flow declaration names its children before any of them
 * exists, and the mechanism submits them later. A divergence between the two would not fail loudly
 * — the children would simply never be gated by the parent that claims them, and the flow would
 * report on work that is not the work running.
 *
 * ⚠️ `ignoreCache` is part of the identity for the same reason it is below. A refresh declares its
 * per-chain decode up front with `deps` on every account sync, so `tx_decoding:<chain>` sat PENDING
 * with `ignoreCache: false` for the whole sync window; keyed by chain alone, pressing "Redecode all
 * transactions" during that window was handed the pending run's promise. The forced decode never
 * reached the backend, and the REDECODE umbrella still settled COMPLETE.
 */
export function decodeActivityId(chain: string, ignoreCache = false): ActivityId {
  return makeActivityId(ActivityKind.TX_DECODING, chain, ignoreCache ? ActivityPart.PULL : ActivityPart.CACHED);
}

/**
 * The identity of one chain's decode within a *targeted* request.
 *
 * ⚠️ The tx refs are part of the identity, not decoration. This was
 * `TX_DECODING:<chain>:PULL` — scoped by chain alone — while the activity is `rerunnable: false`
 * and its payload is the request. Two different tx sets on one chain therefore deduped onto each
 * other and the second caller was handed the first run's promise, so its transactions were never
 * decoded.
 */
export function targetedDecodeActivityId(chain: string, txRefs: readonly string[]): ActivityId {
  return makeActivityId(ActivityKind.TX_DECODING, chain, ActivityPart.PULL, asScope(txRefs));
}

/**
 * The identity of a block-event decode.
 *
 * ⚠️ Block events are ethereum-only, which previously justified a bare singleton id — but "only one
 * chain" is not "only one request". The block numbers are the request, so they belong in the id for
 * the same reason as above.
 */
export function blockDecodeActivityId(blockNumbers: readonly number[]): ActivityId {
  return makeActivityId(ActivityKind.ETH_BLOCK_DECODING, asScope(blockNumbers));
}
