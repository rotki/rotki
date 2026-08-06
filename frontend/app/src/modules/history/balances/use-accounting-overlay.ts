import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { type BigNumber, Zero } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useHistoricalBalancesApi } from '@/modules/balances/api/use-historical-balances-api';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import {
  mergeSameScopeBuckets,
  pairKey,
  PairOverlayStatus,
  type PreparedBucket,
  resolveStatus,
  valueAt,
} from '@/modules/history/balances/accounting-overlay-helpers';
import { downsample, SPARKLINE_MAX_POINTS } from '@/modules/history/balances/sparkline';
import { type HistoricalBalanceSeriesPayload, HistoricalBalanceSeriesResponse } from '@/modules/history/balances/types';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

// Re-exported so existing imports of these from this module keep working.
export { PairOverlayStatus };

/** Aggregate overlay state: `disabled` (off), `loading` (all series in flight), `ready` (some resolved). */
export const AccountingOverlayState = {
  DISABLED: 'disabled',
  LOADING: 'loading',
  READY: 'ready',
} as const;

export type AccountingOverlayState = typeof AccountingOverlayState[keyof typeof AccountingOverlayState];

/** The overlay column toggle: `none` hides it, `balance` shows balance-after-event. */
export const OverlayMode = {
  BALANCE: 'balance',
  NONE: 'none',
} as const;

export type OverlayMode = typeof OverlayMode[keyof typeof OverlayMode];

export interface AccountingOverlayBucket {
  location: string;
  protocol: string | null;
  balance: BigNumber;
}

/** A single point on the balance-over-time sparkline: unix seconds + total balance as a number. */
export interface SparklinePoint {
  time: number;
  value: number;
}

/** The minimal identity an event contributes: its account, asset (and optional location). */
export interface OverlayPair {
  locationLabel: string;
  asset: string;
  location?: string;
}

interface AccountingOverlayParams {
  enabled: MaybeRefOrGetter<boolean>;
  /** Distinct `(account, asset)` pairs present in the loaded events; each gets a series fetch. */
  pairs: MaybeRefOrGetter<OverlayPair[]>;
  fromTimestamp?: MaybeRefOrGetter<number | undefined>;
  toTimestamp?: MaybeRefOrGetter<number | undefined>;
}

interface PairSeries {
  status: PairOverlayStatus;
  buckets: PreparedBucket[];
  error?: string;
}

export interface UseAccountingOverlayReturn {
  state: ComputedRef<AccountingOverlayState>;
  statusFor: (locationLabel: string, asset: string) => PairOverlayStatus;
  balanceAfter: (locationLabel: string, asset: string, timestampMs: number) => BigNumber | undefined;
  bucketsAt: (locationLabel: string, asset: string, timestampMs: number) => AccountingOverlayBucket[];
  /** Total-balance points for the full trajectory up to `timestampMs`, for a sparkline. */
  seriesUpTo: (locationLabel: string, asset: string, timestampMs: number) => SparklinePoint[];
  /**
   * Lets a rendered cell declare the `(account, asset)` it needs, so the overlay fetches it even
   * when the pair isn't in the view-derived set — e.g. an asset movement linked into another
   * group at render time, which never appears in the paginated `groups.data`.
   */
  ensurePair: (pair: OverlayPair) => void;
  refresh: () => Promise<void>;
}

/** Backend returns this message (404) when the scope has no computed metrics yet. */
const NO_DATA_MESSAGE = 'No historical data found';

/**
 * Drives the "balance at event" accounting overlay on the history events page.
 *
 * Every event already carries its account (`location_label`), asset and timestamp — exactly
 * what `/balances/historical/asset/series` needs. So the overlay needs no extra filter: it
 * derives the distinct `(account, asset)` pairs from the loaded events, fetches one series
 * per pair (cached), and exposes a local step-function lookup so each row resolves its own
 * `balance_after` with zero per-row backend calls.
 */
export function useAccountingOverlay(params: AccountingOverlayParams): UseAccountingOverlayReturn {
  const { enabled, fromTimestamp, pairs, toTimestamp } = params;

  const { t } = useI18n({ useScope: 'global' });
  const { fetchHistoricalBalanceSeries } = useHistoricalBalancesApi();
  const { submitTask } = useNativeTask();

  // pairKey -> series state.
  const cache = shallowRef<Map<string, PairSeries>>(new Map());
  // Pairs declared by rendered cells that the view-derived set may not cover (e.g. linked
  // asset movements). pairKey -> pair; fetched alongside the view's pairs.
  const requestedPairs = shallowRef<Map<string, OverlayPair>>(new Map());
  // Monotonic scope id; bumped when the time range or toggle changes so in-flight results
  // for a previous scope are discarded and the cache is rebuilt.
  const scopeId = shallowRef<number>(0);
  // Guards the incremental pair watcher from firing before the first refresh has established a
  // scope. Without it, pairs arriving during the initial (debounced) refresh trigger a fetch
  // under the old scope, which refresh then supersedes — duplicating every request and leaving
  // entries whose duplicate got cancelled stuck on 'loading' forever.
  const initialized = shallowRef<boolean>(false);

  const state = computed<AccountingOverlayState>(() => {
    if (!toValue(enabled))
      return AccountingOverlayState.DISABLED;

    const statuses = Array.from(get(cache).values(), entry => entry.status);
    if (statuses.length > 0 && statuses.every(status => status === PairOverlayStatus.LOADING))
      return AccountingOverlayState.LOADING;
    return AccountingOverlayState.READY;
  });

  function setEntry(key: string, entry: PairSeries): void {
    const next = new Map(get(cache));
    next.set(key, entry);
    set(cache, next);
  }

  /**
   * Maps a finished task outcome to the entry to store, or `null` when the current state
   * should be kept (the task was cancelled / skipped rather than failing for real).
   */
  function entryFromOutcome(outcome: Result<HistoricalBalanceSeriesResponse, TaskError>): PairSeries | null {
    const response = isErr(outcome) ? undefined : outcome.value;
    if (isErr(outcome)) {
      if (!isActionable(outcome.error))
        return null;
      if (outcome.error.message.includes(NO_DATA_MESSAGE))
        return { status: PairOverlayStatus.EMPTY, buckets: [] };

      return {
        status: PairOverlayStatus.ERROR,
        buckets: [],
        error: outcome.error.message,
      };
    }

    if (!response)
      return null;

    const parsed = HistoricalBalanceSeriesResponse.parse(response);
    const buckets = mergeSameScopeBuckets(parsed.entries.map<PreparedBucket>(entry => ({
      location: entry.location,
      // The backend tags plain-wallet series as either null or '' (empty string) — normalise
      // both to null so they share a scope key (and render consistently as "Wallet").
      protocol: entry.protocol ?? null,
      times: entry.times,
      values: entry.values,
    })));
    return { status: resolveStatus(buckets.length, parsed.processingRequired), buckets };
  }

  async function fetchPairSeries(pair: OverlayPair, currentScope: number): Promise<void> {
    const key = pairKey(pair.locationLabel, pair.asset);
    setEntry(key, { status: PairOverlayStatus.LOADING, buckets: [] });

    const from = toValue(fromTimestamp);
    const to = toValue(toTimestamp);
    const payload: HistoricalBalanceSeriesPayload = {
      asset: pair.asset,
      locationLabel: pair.locationLabel,
      ...(pair.location ? { location: pair.location } : {}),
      ...(from ? { fromTimestamp: from } : {}),
      ...(to ? { toTimestamp: to } : {}),
    };

    try {
      // Per-request id keyed by the (account, asset) pair *and the date range*: we fan out one
      // task per pair concurrently, so the ids must differ or `submitTask` would dedup distinct
      // pairs — and a range change is a different question about the same pair. Without the
      // timestamps, changing the range while a series was in flight deduped onto the old request,
      // so the series never re-fetched and the cell sat on LOADING forever.
      const outcome = await submitTask<HistoricalBalanceSeriesResponse>({
        id: makeActivityId(ActivityKind.HISTORICAL_BALANCES, ActivityPart.SERIES, pair.locationLabel, pair.asset, from ?? 0, to ?? 0),
        kind: ActivityKind.HISTORICAL_BALANCES,
        rerunnable: false,
        run: async ({ runTask }): Promise<Result<HistoricalBalanceSeriesResponse, TaskError>> => mapResult(
          await runTask<HistoricalBalanceSeriesResponse>(
            async () => fetchHistoricalBalanceSeries(payload),
          ),
          value => value,
        ),
        subtitle: activityLabelFor(msg.$t('task_center.activity.historical_balances.series'), { asset: pair.asset }),
        title: t('task_center.group.historical_balances'),
      });

      if (get(scopeId) !== currentScope)
        return; // scope changed while awaiting; drop stale result

      const entry = entryFromOutcome(outcome);
      if (entry)
        setEntry(key, entry);
    }
    catch (error_: unknown) {
      if (get(scopeId) === currentScope)
        setEntry(key, { status: PairOverlayStatus.ERROR, buckets: [], error: getErrorMessage(error_) });
    }
  }

  /** Fetch the known pairs (view-derived + requested) whose cache entry matches `shouldFetch`. */
  function fetchPairsWhere(shouldFetch: (entry: PairSeries | undefined) => boolean): void {
    if (!toValue(enabled))
      return;

    const currentScope = get(scopeId);
    const cached = get(cache);
    for (const pair of [...toValue(pairs), ...get(requestedPairs).values()]) {
      if (!pair.locationLabel || !pair.asset)
        continue;
      if (shouldFetch(cached.get(pairKey(pair.locationLabel, pair.asset))))
        startPromise(fetchPairSeries(pair, currentScope));
    }
  }

  /** Fetch any pairs in the current set that aren't cached yet (for the current scope). */
  function fetchMissing(): void {
    fetchPairsWhere(entry => entry === undefined);
  }

  /** Register a pair a rendered cell needs, fetching it immediately when we're past init. */
  function ensurePair(pair: OverlayPair): void {
    if (!pair.locationLabel || !pair.asset)
      return;

    const key = pairKey(pair.locationLabel, pair.asset);
    if (get(requestedPairs).has(key) || get(cache).has(key))
      return;

    const next = new Map(get(requestedPairs));
    next.set(key, pair);
    set(requestedPairs, next);

    // Before the first refresh, refresh()'s fetchMissing will pick it up; after, fetch it now.
    if (get(initialized) && toValue(enabled))
      startPromise(fetchPairSeries(pair, get(scopeId)));
  }

  /** Drop the cache and refetch from scratch for the current scope. */
  async function refresh(): Promise<void> {
    set(scopeId, get(scopeId) + 1);
    set(cache, new Map());
    set(initialized, true);
    fetchMissing();
  }

  function statusFor(locationLabel: string, asset: string): PairOverlayStatus {
    return get(cache).get(pairKey(locationLabel, asset))?.status ?? PairOverlayStatus.LOADING;
  }

  function balanceAfter(locationLabel: string, asset: string, timestampMs: number): BigNumber | undefined {
    const entry = get(cache).get(pairKey(locationLabel, asset));
    if (entry?.status !== PairOverlayStatus.READY)
      return undefined;

    const tsSec = Math.floor(timestampMs / 1000);
    return entry.buckets.reduce<BigNumber>((sum, bucket) => sum.plus(valueAt(bucket, tsSec)), Zero);
  }

  function bucketsAt(locationLabel: string, asset: string, timestampMs: number): AccountingOverlayBucket[] {
    const entry = get(cache).get(pairKey(locationLabel, asset));
    if (!entry)
      return [];

    const tsSec = Math.floor(timestampMs / 1000);
    return entry.buckets.map<AccountingOverlayBucket>(bucket => ({
      location: bucket.location,
      protocol: bucket.protocol,
      balance: valueAt(bucket, tsSec),
    }));
  }

  function seriesUpTo(locationLabel: string, asset: string, timestampMs: number): SparklinePoint[] {
    const entry = get(cache).get(pairKey(locationLabel, asset));
    if (entry?.status !== PairOverlayStatus.READY)
      return [];

    const end = Math.floor(timestampMs / 1000);
    const totalAt = (tsSec: number): number =>
      entry.buckets.reduce<BigNumber>((sum, bucket) => sum.plus(valueAt(bucket, tsSec)), Zero).toNumber();

    // Every change-point up to (and including) the event — the full balance trajectory.
    const interior = entry.buckets.flatMap(bucket => bucket.times).filter(time => time < end);
    const ordered = [...new Set([end, ...interior])].sort((a, b) => a - b);

    return downsample(ordered, SPARKLINE_MAX_POINTS).map<SparklinePoint>(time => ({ time, value: totalAt(time) }));
  }

  // Scope changes (time range / toggle) reset the cache and refetch.
  watchDebounced(
    [
      (): boolean => toValue(enabled),
      (): number | undefined => toValue(fromTimestamp),
      (): number | undefined => toValue(toTimestamp),
    ],
    () => startPromise(refresh()),
    { debounce: 400, immediate: true },
  );

  // The visible pair set grows as more events load; fetch the newcomers. Gated on the first
  // refresh so it never races ahead of the initial scope (see `initialized`).
  watch((): OverlayPair[] => toValue(pairs), () => {
    if (get(initialized))
      fetchMissing();
  }, { deep: true });

  return {
    state,
    statusFor,
    balanceAfter,
    bucketsAt,
    seriesUpTo,
    ensurePair,
    refresh,
  };
}
