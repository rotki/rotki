import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { HistoricalBalancesAtEventsResponse } from '@/modules/history/balances/types';
import { type BigNumber, Zero } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useHistoricalBalancesApi } from '@/modules/balances/api/use-historical-balances-api';
import { PairOverlayStatus } from '@/modules/history/balances/accounting-overlay-helpers';

export { PairOverlayStatus };

export const AccountingOverlayState = {
  DISABLED: 'disabled',
  LOADING: 'loading',
  READY: 'ready',
} as const;

export type AccountingOverlayState = typeof AccountingOverlayState[keyof typeof AccountingOverlayState];

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

export interface SparklinePoint {
  time: number;
  value: number;
}

interface EventSnapshot {
  status: PairOverlayStatus;
  buckets: AccountingOverlayBucket[];
}

function snapshotFromEntry(entry: HistoricalBalancesAtEventsResponse['entries'][string] | undefined): EventSnapshot {
  if (!entry)
    return { status: PairOverlayStatus.ERROR, buckets: [] };
  if (entry.processingRequired)
    return { status: PairOverlayStatus.PROCESSING, buckets: entry.buckets };
  return {
    status: entry.buckets.length > 0 ? PairOverlayStatus.READY : PairOverlayStatus.EMPTY,
    buckets: entry.buckets,
  };
}

interface AccountingOverlayParams {
  enabled: MaybeRefOrGetter<boolean>;
  eventIdentifiers: MaybeRefOrGetter<number[]>;
}

export interface UseAccountingOverlayReturn {
  state: ComputedRef<AccountingOverlayState>;
  statusFor: (identifier: number) => PairOverlayStatus;
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

  const state = computed<AccountingOverlayState>(() => {
    if (!toValue(enabled))
      return AccountingOverlayState.DISABLED;
    const active = get(activeIdentifiers);
    return active.length > 0 && active.every(id => statusFor(id) === PairOverlayStatus.LOADING)
      ? AccountingOverlayState.LOADING
      : AccountingOverlayState.READY;
  });

  async function fetchMissing(): Promise<void> {
    if (disposed)
      return;
    const currentGeneration = generation;
    const missing = get(activeIdentifiers).filter(id => !get(cache).has(id));
    const next = new Map(get(cache));
    for (const id of missing)
      next.set(id, { status: PairOverlayStatus.LOADING, buckets: [] });
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
      catch {
        if (currentGeneration !== generation)
          return;
        const updated = new Map(get(cache));
        for (const id of batch)
          updated.set(id, { status: PairOverlayStatus.ERROR, buckets: [] });
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

  function statusFor(identifier: number): PairOverlayStatus {
    return get(cache).get(identifier)?.status ?? PairOverlayStatus.LOADING;
  }

  function balanceAfter(identifier: number): BigNumber | undefined {
    const entry = get(cache).get(identifier);
    return entry?.status === PairOverlayStatus.READY
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

  return { state, statusFor, balanceAfter, bucketsAt, registerEvent, refresh };
}
