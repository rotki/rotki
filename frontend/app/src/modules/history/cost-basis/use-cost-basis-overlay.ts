import type { CostBasisEntry } from '@/modules/history/cost-basis/types';
import { startPromise } from '@shared/utils';
import { tryOnScopeDispose, useTimeoutFn } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { computed, type MaybeRefOrGetter, shallowRef, toValue, watch } from 'vue';
import { watchDebounced } from '@/modules/core/common/async/scoped-timers';
import { logger } from '@/modules/core/common/logging/logging';
import { useCostBasisApi } from '@/modules/history/cost-basis/use-cost-basis-api';

/** Availability of the cost basis of an event. */
export const CostBasisStatus = {
  EMPTY: 'empty',
  ERROR: 'error',
  LOADING: 'loading',
  PROCESSING: 'processing',
  READY: 'ready',
} as const;

export type CostBasisStatus = typeof CostBasisStatus[keyof typeof CostBasisStatus];

/** The backend rejects a request for more events than this. */
const BATCH_SIZE = 500;

/** How long after a failed batch its events are fetched again. */
const RETRY_DELAY_MS = 15_000;

interface EventCostBasis {
  status: CostBasisStatus;
  entries: CostBasisEntry[];
}

interface CostBasisOverlayParams {
  enabled: MaybeRefOrGetter<boolean>;
  eventIdentifiers: MaybeRefOrGetter<number[]>;
}

export interface UseCostBasisOverlayReturn {
  statusFor: (identifier: number) => CostBasisStatus;
  entriesFor: (identifier: number) => CostBasisEntry[];
  /** Register a rendered event absent from the page groups; returns its cleanup function. */
  registerEvent: (identifier: number) => () => void;
  refresh: () => Promise<void>;
  /** Fetch again the events still waiting for processing, keeping what is shown until then. */
  refreshProcessing: () => Promise<void>;
}

/**
 * Fetches the cost basis of the page's events in batches and keeps it until the overlay is turned
 * off or refreshed.
 *
 * @remarks
 * An event the response has no entries for affects no lots, which is a result and not a failure,
 * so it is kept as empty unless the response marks it as waiting for processing. A failed batch is
 * shown as an error and fetched again after a delay, or sooner on the next change to the active
 * events.
 */
export function useCostBasisOverlay({ enabled, eventIdentifiers }: CostBasisOverlayParams): UseCostBasisOverlayReturn {
  const { fetchEventsCostBasis } = useCostBasisApi();
  const cache = shallowRef<Map<number, EventCostBasis>>(new Map());
  const registered = shallowRef<Map<number, number>>(new Map());
  let generation = 0;
  let disposed = false;

  // `fetchMissing` fetches the events of a failed batch again, as `needsFetch` lets errors through.
  const retry = useTimeoutFn(() => startPromise(fetchMissing()), RETRY_DELAY_MS, { immediate: false });

  const activeIdentifiers = computed<number[]>(() => toValue(enabled)
    ? [...new Set([...toValue(eventIdentifiers), ...get(registered).keys()])]
    : []);

  function needsFetch(identifier: number): boolean {
    const status = get(cache).get(identifier)?.status;
    return status === undefined || status === CostBasisStatus.ERROR;
  }

  function store(identifiers: number[], toCostBasis: (identifier: number) => EventCostBasis): void {
    const next = new Map(get(cache));
    for (const identifier of identifiers)
      next.set(identifier, toCostBasis(identifier));
    set(cache, next);
  }

  async function fetchBatches(identifiers: number[]): Promise<void> {
    const currentGeneration = generation;
    for (let offset = 0; offset < identifiers.length; offset += BATCH_SIZE) {
      const batch = identifiers.slice(offset, offset + BATCH_SIZE);
      try {
        const response = await fetchEventsCostBasis(batch);
        if (currentGeneration !== generation)
          return;
        const entries = new Map(Object.entries(response.entries));
        const stale = new Set(response.stale);
        store(batch, (identifier) => {
          if (stale.has(identifier))
            return { entries: [], status: CostBasisStatus.PROCESSING };
          const found = entries.get(String(identifier)) ?? [];
          return { entries: found, status: found.length > 0 ? CostBasisStatus.READY : CostBasisStatus.EMPTY };
        });
      }
      catch (error: unknown) {
        logger.error(error);
        if (currentGeneration !== generation)
          return;
        store(batch, () => ({ entries: [], status: CostBasisStatus.ERROR }));
        retry.start();
      }
    }
  }

  async function fetchMissing(): Promise<void> {
    if (disposed)
      return;
    const missing = get(activeIdentifiers).filter(needsFetch);
    // Replacing the cache invalidates every rendered cell, which scrolling would do on each tick.
    if (missing.length === 0)
      return;
    store(missing, () => ({ entries: [], status: CostBasisStatus.LOADING }));
    await fetchBatches(missing);
  }

  async function refreshProcessing(): Promise<void> {
    if (disposed)
      return;
    await fetchBatches(get(activeIdentifiers).filter(identifier => statusFor(identifier) === CostBasisStatus.PROCESSING));
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

  function statusFor(identifier: number): CostBasisStatus {
    return get(cache).get(identifier)?.status ?? CostBasisStatus.LOADING;
  }

  function entriesFor(identifier: number): CostBasisEntry[] {
    return get(cache).get(identifier)?.entries ?? [];
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

  return { entriesFor, refresh, refreshProcessing, registerEvent, statusFor };
}
