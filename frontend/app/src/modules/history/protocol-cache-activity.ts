import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { type ActivityId, ActivityKind } from '@/modules/task-center/core/types';

/**
 * One protocol's cache query on one chain, as a row beneath the work that triggered it.
 *
 * @remarks
 * A row rather than an activity because nothing declares the set. The backend mints these pairs as
 * its decoders reach them and never says how many are coming, so children minted from arriving
 * frames would give their parent a denominator that grows as the run proceeds — a bar that runs
 * backwards — and a pair whose query fails sends no terminal frame at all, so its row would stay
 * live forever. Sub-items that have no activity of their own may carry their own counts; what a
 * detail may never restate is the *activity's* status.
 */
interface ProtocolCacheRow {
  /** The backend's own spelling (`ethereum`), not the chain id an activity is keyed by (`eth`). */
  readonly chain: string;
  readonly protocol: string;
  readonly processed: number;
  readonly total: number;
}

/**
 * The protocol caches being filled under one activity.
 *
 * Per-row percentages are honest, because `processed`/`total` describe that one pair. There is
 * deliberately no aggregate: summing across rows measures only the pairs seen so far.
 */
export interface ProtocolCacheDetail {
  readonly protocols: readonly ProtocolCacheRow[];
}

/**
 * The user-initiated cache refresh, from the data-management screen.
 *
 * No key: one refresh runs at a time and the id has nothing to distinguish. Declared as a
 * descriptor anyway so the producer and the readers that ask whether it is running compose the
 * same id from one place.
 */
export const protocolCacheActivity = defineActivity<void, readonly [], ProtocolCacheDetail>({
  key: () => [],
  kind: ActivityKind.PROTOCOL_CACHE,
});

/** The identity of the user-initiated cache refresh. See {@link protocolCacheActivity}. */
export function protocolCacheActivityId(): ActivityId {
  return protocolCacheActivity.id();
}
