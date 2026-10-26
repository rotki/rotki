import type { HistoricalBalanceDivergencePayload } from '@/modules/history/balances/types';
import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';

/** One account's balance series for one asset. */
export interface OverlaySeriesSubject {
  readonly locationLabel: string;
  readonly asset: string;
}

/**
 * Processing the historical balances. A singleton: its id is the bare kind, and the backend's
 * processing progress frames report onto it.
 */
export const historicalBalancesActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.HISTORICAL_BALANCES,
});

/** Loading one account's balance series for one asset, keyed by both. */
export const overlaySeriesActivity = defineActivity<OverlaySeriesSubject, readonly [string, string]>({
  key: subject => [subject.locationLabel, subject.asset],
  kind: ActivityKind.HISTORICAL_BALANCES,
  part: ActivityPart.SERIES,
});

/**
 * Looking for where a balance diverges from its events, keyed by every field of the request.
 *
 * @remarks
 * An absent tolerance is `0` and an absent upper bound is `latest`, so each stays part of the
 * identity rather than collapsing two requests onto one.
 */
export const balanceDivergenceActivity = defineActivity<
  HistoricalBalanceDivergencePayload,
  readonly [string, string, string, string | number, string | number]
>({
  key: subject => [subject.asset, subject.address, subject.evmChain, subject.tolerance ?? 0, subject.toTimestamp ?? 'latest'],
  kind: ActivityKind.HISTORICAL_BALANCES,
  part: ActivityPart.DIVERGENCE,
});

/** Comparing the derived balances with the live chain balances. A singleton under the kind. */
export const currentBalanceDetectionActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.HISTORICAL_BALANCES,
  part: ActivityPart.DETECT,
});
