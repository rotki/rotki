import type { Raw, Ref } from 'vue';

/** One resolved key/value pair, as a batch fetch yields it. */
interface CacheEntry<T> {
  key: string;
  item: T;
}

/**
 * A batch-fetch resolving many keys at once.
 *
 * @remarks
 * Yields its {@link CacheEntry} items through a lazy iterator rather than an array, so a large batch
 * is not materialised twice.
 */
export type CacheFetch<T> = (keys: string[]) => Promise<() => IterableIterator<CacheEntry<T>>>;

/**
 * The persistent storage of an item cache: the values plus their bookkeeping.
 *
 * @remarks
 * Kept apart from the cache logic in `use-item-cache.ts` so it can live in a Pinia store and outlive
 * the composable that reads it.
 *
 * That outliving is the whole point of injecting it: a `createSharedComposable` cache is disposed
 * once its last subscriber goes away, so a cache holding its own storage is wiped every time the
 * user navigates away from the only page reading it. Holding the storage in a store instead makes
 * it app-lifetime, and the composable rebinds to whatever is already there.
 */
export interface ItemCacheStorage<T> {
  /** Resolved values keyed by identifier. */
  cache: Ref<Record<string, T | null>>;
  /** Per-key expiry timestamps backing the LRU and the staleness checks. */
  recent: Map<string, number>;
  /** Identifiers that could not be resolved, with their expiry timestamps. */
  unknown: Map<string, number>;
}

/**
 * Creates a fresh {@link ItemCacheStorage} container.
 *
 * @remarks
 * The `markRaw` brand is load-bearing: without it Pinia deeply unwraps `cache` from a `Ref` into a
 * plain value and wraps the two maps in reactive proxies, and neither survives the cache's own
 * bookkeeping.
 */
export function createItemCacheStorage<T>(): Raw<ItemCacheStorage<T>> {
  return markRaw<ItemCacheStorage<T>>({
    cache: shallowRef<Record<string, T | null>>({}),
    recent: new Map<string, number>(),
    unknown: new Map<string, number>(),
  });
}
