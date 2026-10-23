import type { Purgeable } from '@/modules/session/purge';
import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { ActivityKind } from '@/modules/task-center/core/types';

/** One purge: the source, and the single target within it when the user picked one. */
export interface PurgeSubject {
  readonly purgeable: Purgeable;
  /** Empty for a purge of the whole source. */
  readonly value: string;
}

/**
 * The sync the user starts, upload or download.
 *
 * @remarks
 * Its id is the bare kind, so `partsOf()` is empty, and a status read with no parts aggregates the
 * whole kind. The sync indicator and the force-sync guard read the kind on purpose: they cover the
 * backend's own scheduled upload, {@link automaticSyncActivity}, too. Only an id comparison tells
 * the two apart.
 */
export const manualSyncActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.SYNC,
});

/**
 * An upload the backend runs on its own schedule, opened by its first progress message. One
 * stable id, so a backup failing every hour replaces its row rather than piling up.
 */
export const automaticSyncActivity = defineActivity<void, readonly [string]>({
  key: () => ['automatic'],
  kind: ActivityKind.SYNC,
});

/**
 * Purging one data source, or one target within it (`purge:transactions:eth`).
 *
 * @remarks
 * What derives from the purged data declares a `staleAfter` edge on a prefix of this key, so a
 * per-target purge satisfies the edge on its whole source too.
 */
export const purgeActivity = defineActivity<PurgeSubject, readonly [Purgeable] | readonly [Purgeable, string]>({
  key: subject => (subject.value ? [subject.purgeable, subject.value] : [subject.purgeable]),
  kind: ActivityKind.PURGE,
});
