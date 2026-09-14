import type { MaybeRefOrGetter } from 'vue';
import type { HistoricalBalancesAtEventsResponse } from '@/modules/history/balances/types';
import { type BigNumber, Zero } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useHistoricalBalancesApi } from '@/modules/balances/api/use-historical-balances-api';
import { logger } from '@/modules/core/common/logging/logging';
import { EventOverlayStatus } from '@/modules/history/balances/accounting-overlay-helpers';

export { EventOverlayStatus };

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

interface EventSnapshot {
  status: EventOverlayStatus;
  buckets: AccountingOverlayBucket[];
}

function snapshotFromEntry(entry: HistoricalBalancesAtEventsResponse['entries'][string] | undefined): EventSnapshot {
  if (!entry)
    return { status: EventOverlayStatus.ERROR, buckets: [] };
  if (entry.processingRequired)
    return { status: EventOverlayStatus.PROCESSING, buckets: entry.buckets };
  return {
    status: entry.buckets.length > 0 ? EventOverlayStatus.READY : EventOverlayStatus.EMPTY,
    buckets: entry.buckets,
  };
}

interface AccountingOverlayParams {
  enabled: MaybeRefOrGetter<boolean>;
  eventIdentifiers: MaybeRefOrGetter<number[]>;
}

export interface UseAccountingOverlayReturn {
  statusFor: (identifier: number) => EventOverlayStatus;
  balanceAfter: (identifier: number) => BigNumber | undefined;
  bucketsAt: (identifier: number) => AccountingOverlayBucket[];
  /** Register a rendered event absent from the page groups; returns its cleanup function. */
  registerEvent: (identifier: number) => () => void;
  refresh: () => Promise<void>;
}

/** Fetch exact event snapshots in page batches, including events linked into rendered groups. */
export function useAccountingOverlay({ enabled, eventIdentifiers }: AccountingOverlayParams): UseAccountingOverlayReturn {
  const { fetchHistoricalBalancesAtEvents } = useHistoricalBalancesApi();
  const cache = shallowRef<Map<number, EventSnapshot>>(new Map());
  const registered = shallowRef<Map<number, number>>(new Map());
  let generation = 0;
  let disposed = false;

  const activeIdentifiers = computed<number[]>(() => toValue(enabled)
    ? [...new Set([...toValue(eventIdentifiers), ...get(registered).keys()])]
    : []);

  /** Whether an event still lacks a usable snapshot, which includes one whose fetch failed. */
  function needsFetch(identifier: number): boolean {
    const status = get(cache).get(identifier)?.status;
    return status === undefined || status === EventOverlayStatus.ERROR;
  }

  /**
   * Fetches a snapshot for every active event that lacks one, 500 identifiers per request.
   *
   * @remarks
   * The endpoint rejects a whole batch when any identifier is unknown, e.g. an event redecoded since
   * the page loaded. A failure is shown but not kept for good: the next change to the active events
   * retries it, instead of leaving every row of the batch on an error until the next sync.
   */
  async function fetchMissing(): Promise<void> {
    if (disposed)
      return;
    const currentGeneration = generation;
    const missing = get(activeIdentifiers).filter(needsFetch);
    const next = new Map(get(cache));
    for (const id of missing)
      next.set(id, { status: EventOverlayStatus.LOADING, buckets: [] });
    set(cache, next);

    for (let offset = 0; offset < missing.length; offset += 500) {
      if (currentGeneration !== generation)
        return;
      const batch = missing.slice(offset, offset + 500);
      try {
        const response = await fetchHistoricalBalancesAtEvents(batch);
        if (currentGeneration !== generation)
          return;
        const entries = new Map(Object.entries(response.entries));
        const updated = new Map(get(cache));
        for (const id of batch) {
          updated.set(id, snapshotFromEntry(entries.get(String(id))));
        }
        set(cache, updated);
      }
      catch (error: unknown) {
        logger.error(error);
        if (currentGeneration !== generation)
          return;
        const updated = new Map(get(cache));
        for (const id of batch)
          updated.set(id, { status: EventOverlayStatus.ERROR, buckets: [] });
        set(cache, updated);
      }
    }
  }

  function registerEvent(identifier: number): () => void {
    const next = new Map(get(registered));
    next.set(identifier, (next.get(identifier) ?? 0) + 1);
    set(registered, next);
    return (): void => {
      const remaining = new Map(get(registered));
      const count = (remaining.get(identifier) ?? 1) - 1;
      if (count > 0)
        remaining.set(identifier, count);
      else
        remaining.delete(identifier);
      set(registered, remaining);
    };
  }

  async function refresh(): Promise<void> {
    generation++;
    set(cache, new Map());
    await fetchMissing();
  }

  function statusFor(identifier: number): EventOverlayStatus {
    return get(cache).get(identifier)?.status ?? EventOverlayStatus.LOADING;
  }

  function balanceAfter(identifier: number): BigNumber | undefined {
    const entry = get(cache).get(identifier);
    return entry?.status === EventOverlayStatus.READY
      ? entry.buckets.reduce((sum, bucket) => sum.plus(bucket.balance), Zero)
      : undefined;
  }

  function bucketsAt(identifier: number): AccountingOverlayBucket[] {
    return get(cache).get(identifier)?.buckets ?? [];
  }

  watch((): boolean => toValue(enabled), () => {
    generation++;
    set(cache, new Map());
  }, { flush: 'sync' });

  watchDebounced(activeIdentifiers, () => startPromise(fetchMissing()), { debounce: 50, immediate: true });
  tryOnScopeDispose(() => {
    disposed = true;
    generation++;
  });

  return { statusFor, balanceAfter, bucketsAt, registerEvent, refresh };
}
