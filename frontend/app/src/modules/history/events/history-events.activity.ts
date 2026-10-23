import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';

/** One transaction lookup from the event form. */
export interface TxLookupSubject {
  /** Bumped per lookup, so a newer lookup of the same hash is a new request. */
  readonly requestId: number;
  readonly txHash: string;
}

/** Fetching how many transactions are still undecoded, which a decode can wait for. */
export const undecodedBreakdownActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.HISTORY_EVENTS,
  part: ActivityPart.UNDECODED,
});

/** Exporting the history events to a file. */
export const historyEventsExportActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.HISTORY_EVENTS,
  part: ActivityPart.EXPORT,
});

/** Automatically matching asset movements to their on-chain counterparts. */
export const assetMovementMatchActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.HISTORY_EVENTS,
  part: ActivityPart.MATCH,
});

/** Automatically matching the two sides of bridge transactions. */
export const bridgeMatchActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.HISTORY_EVENTS,
  part: ActivityPart.BRIDGE,
});

/**
 * Looking a transaction up to fill the event form.
 *
 * @remarks
 * A new lookup cancels every older one by the `lookup` prefix before it submits, so only the
 * latest request's result reaches the form.
 */
export const txLookupActivity = defineActivity<TxLookupSubject, readonly [number, string]>({
  key: subject => [subject.requestId, subject.txHash],
  kind: ActivityKind.HISTORY_EVENTS,
  part: ActivityPart.LOOKUP,
});
