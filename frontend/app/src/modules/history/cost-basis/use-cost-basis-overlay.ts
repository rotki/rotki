import type { MaybeRefOrGetter, Ref } from 'vue';
import type { CostBasisEntry } from '@/modules/history/cost-basis/types';
import { startPromise } from '@shared/utils';
import { logger } from '@/modules/core/common/logging/logging';
import { useCostBasisApi } from '@/modules/history/cost-basis/use-cost-basis-api';

/** Availability of the cost basis of an event. */
export const CostBasisStatus = {
  EMPTY: 'empty',
  ERROR: 'error',
  LOADING: 'loading',
  READY: 'ready',
} as const;

export type CostBasisStatus = typeof CostBasisStatus[keyof typeof CostBasisStatus];

/** The backend rejects a request for more events than this. */
const BATCH_SIZE = 500;

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
  /** Whether the cost basis waits to be processed, so what is shown may be missing or outdated. */
  stale: Readonly<Ref<boolean>>;
}

/**
 * Fetches the cost basis of the page's events in batches and keeps it until the overlay is turned
 * off or refreshed.
 *
 * @remarks
 * An event the response has no entries for affects no lots, which is a result and not a failure,
 * so it is kept as empty. A failed batch is shown as an error and fetched again on the next
 * change to the active events.
 */
export function useCostBasisOverlay({ enabled, eventIdentifiers }: CostBasisOverlayParams): UseCostBasisOverlayReturn {
  const { fetchEventsCostBasis } = useCostBasisApi();
  const cache = shallowRef<Map<number, EventCostBasis>>(new Map());
  const registered = shallowRef<Map<number, number>>(new Map());
  const stale = shallowRef<boolean>(false);
  let generation = 0;
  let disposed = false;

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

  async function fetchMissing(): Promise<void> {
    if (disposed)
      return;
    const currentGeneration = generation;
    const missing = get(activeIdentifiers).filter(needsFetch);
    store(missing, () => ({ entries: [], status: CostBasisStatus.LOADING }));

    for (let offset = 0; offset < missing.length; offset += BATCH_SIZE) {
      const batch = missing.slice(offset, offset + BATCH_SIZE);
      try {
        const response = await fetchEventsCostBasis(batch);
        if (currentGeneration !== generation)
          return;
        const entries = new Map(Object.entries(response.entries));
        set(stale, response.stale);
        store(batch, (identifier) => {
          const found = entries.get(String(identifier)) ?? [];
          return { entries: found, status: found.length > 0 ? CostBasisStatus.READY : CostBasisStatus.EMPTY };
        });
      }
      catch (error: unknown) {
        logger.error(error);
        if (currentGeneration !== generation)
          return;
        store(batch, () => ({ entries: [], status: CostBasisStatus.ERROR }));
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

  return { entriesFor, refresh, registerEvent, stale: readonly(stale), statusFor };
}
