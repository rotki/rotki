import type { ComputedRef, DeepReadonly, MaybeRefOrGetter, Ref } from 'vue';
import { assert } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { logger } from '@/modules/core/common/logging/logging';

const CACHE_EXPIRY = 1000 * 60 * 10;
const CACHE_SIZE = 500;
const DEBOUNCE_TIME = 800;

interface CacheEntry<T> {
  key: string;
  item: T;
}

/**
 * A batch-fetch function that resolves multiple keys at once.
 * Returns a factory that yields {@link CacheEntry} items via an iterator,
 * allowing lazy consumption of potentially large result sets.
 */
type CacheFetch<T> = (keys: string[]) => Promise<() => IterableIterator<CacheEntry<T>>>;

interface CacheOptions {
  /** Debounce interval (ms) before a queued batch is fetched. @default 800 */
  debounceInMs?: number;
  /** Time-to-live (ms) for cached entries before they become stale. @default 600_000 (10 min) */
  expiry?: number;
  /** Maximum number of entries kept in the LRU cache. @default 500 */
  size?: number;
}

interface ItemCacheReturn<T> {
  /** Readonly reactive record of cached values (keyed by identifier). */
  cache: DeepReadonly<Ref<Record<string, T | null>>>;
  /** Map of identifiers that could not be resolved, with their expiry timestamps. */
  unknown: Map<string, number>;
  /** Returns whether the given identifier is currently being fetched (non-reactive). */
  getIsPending: (identifier: string) => boolean;
  /** Reactive computed that tracks whether the given identifier is currently being fetched. */
  isPending: (identifier: MaybeRefOrGetter<string>) => ComputedRef<boolean>;
  /** Synchronously returns the cached value for `key`, queueing a fetch if missing. */
  resolve: (key: string) => T | null;
  /** Returns a reactive computed that resolves `key`, queueing a fetch if missing. */
  useResolve: (key: MaybeRefOrGetter<string>) => ComputedRef<T | null>;
  /** Clears all cached data, pending state, and unknown entries. */
  reset: () => void;
  /** Forces a re-fetch of the given key regardless of its current cache state. */
  refresh: (key: string) => void;
  /** Removes a key from the cache and the unknown map. */
  deleteCacheKey: (key: string) => void;
  /** Queues a key for fetching unless it is already in the unknown map and not yet expired. */
  queueIdentifier: (key: string) => void;
}

/**
 * Creates a debounced, LRU-bounded, reactive item cache backed by a batch-fetch function.
 *
 * Keys requested via {@link ItemCacheReturn.resolve resolve}, {@link ItemCacheReturn.useResolve useResolve},
 * or {@link ItemCacheReturn.queueIdentifier queueIdentifier} are accumulated into a batch and fetched
 * together after a debounce interval. Resolved items are stored in a size-limited LRU cache with
 * configurable expiry. Unresolvable keys are tracked in an `unknown` map to avoid repeated lookups.
 *
 * Internally uses `shallowRef` + `triggerRef` for the cache and pending state, so that batch
 * operations (processing N items) trigger only a single reactive notification per ref.
 *
 * @param fetch - Batch-fetch function that resolves an array of keys into cache entries.
 * @param options - Optional configuration for debounce timing, expiry, and cache size.
 */
export function createItemCache<T>(
  fetch: CacheFetch<T>,
  options: CacheOptions = {},
): ItemCacheReturn<T> {
  const { debounceInMs = DEBOUNCE_TIME, expiry = CACHE_EXPIRY, size = CACHE_SIZE } = options;
  const recent: Map<string, number> = new Map();
  const unknown: Map<string, number> = new Map();
  const cache = shallowRef<Record<string, T | null>>({});
  const pending = shallowRef<Record<string, boolean>>({});
  const batch = new Set<string>();

  const deleteCacheKey = (key: string): void => {
    delete get(cache)[key];
    triggerRef(cache);

    if (unknown.has(key))
      unknown.delete(key);
  };

  const setPending = (key: string): void => {
    get(pending)[key] = true;
    triggerRef(pending);

    batch.add(key);
  };

  const put = (key: string, item: T): void => {
    recent.delete(key);

    if (recent.size === size) {
      logger.debug(`Hit cache size of ${size} going to evict items`);
      const removeKey = recent.keys().next().value;
      assert(removeKey, 'removeKey is null or undefined');
      recent.delete(removeKey);
      delete get(cache)[removeKey];
      if (unknown.has(removeKey))
        unknown.delete(removeKey);
    }
    recent.set(key, Date.now() + expiry);
    get(cache)[key] = item;
  };

  const fetchBatch = useDebounceFn(() => {
    if (batch.size === 0)
      return;

    const currentBatch = [...batch];
    batch.clear();
    startPromise(processBatch(currentBatch));
  }, debounceInMs);

  async function processBatch(keys: string[]): Promise<void> {
    try {
      const batchResult = await fetch(keys);
      for (const { item, key } of batchResult()) {
        if (item) {
          put(key, item);
        }
        else {
          if (import.meta.env.VITE_VERBOSE_CACHE)
            logger.debug(`unknown key: ${key}`);

          recent.delete(key);
          delete get(cache)[key];
          if (unknown.has(key))
            unknown.delete(key);

          unknown.set(key, Date.now() + expiry);
        }
      }
    }
    catch (error) {
      logger.error(error);
    }
    finally {
      const pendingObj = get(pending);
      for (const key of keys) delete pendingObj[key];
      triggerRef(pending);
    }
    triggerRef(cache);
  }

  const queueIdentifier = (key: string): void => {
    const unknownExpiry = unknown.get(key);
    if (unknownExpiry && unknownExpiry >= Date.now())
      return;

    if (unknown.has(key))
      unknown.delete(key);

    setPending(key);
    startPromise(fetchBatch());
  };

  /**
   * Ensures the given key is queued for fetching if it's not already cached or pending.
   * Refreshes the cache expiry for entries that haven't expired yet.
   */
  const ensureQueued = (key: string): void => {
    const cached = get(cache)[key];
    const now = Date.now();
    let valid = false;
    if (recent.has(key) && cached) {
      const cacheExpiry = recent.get(key);
      recent.delete(key);

      if (cacheExpiry && cacheExpiry > now) {
        valid = true;
        recent.set(key, now + expiry);
      }
    }

    if (!get(pending)[key] && !valid)
      queueIdentifier(key);
  };

  const resolve = (key: string): T | null => {
    ensureQueued(key);
    return get(cache)[key] ?? null;
  };

  const useResolve = (key: MaybeRefOrGetter<string>): ComputedRef<T | null> => {
    ensureQueued(toValue(key));
    return computed(() => get(cache)[toValue(key)] ?? null);
  };

  const refresh = (key: string): void => {
    const now = Date.now();
    recent.set(key, now + expiry);
    if (unknown.has(key))
      unknown.delete(key);

    queueIdentifier(key);
  };

  const getIsPending = (identifier: string): boolean => get(pending)[identifier] ?? false;

  const isPending = (
    identifier: MaybeRefOrGetter<string>,
  ): ComputedRef<boolean> => computed<boolean>(() => getIsPending(toValue(identifier)));

  const reset = (): void => {
    set(pending, {});
    set(cache, {});
    batch.clear();
    recent.clear();
    unknown.clear();
  };

  return {
    cache: readonly(cache),
    deleteCacheKey,
    getIsPending,
    isPending,
    queueIdentifier,
    refresh,
    reset,
    resolve,
    useResolve,
    unknown,
  };
}
