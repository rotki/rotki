import type { ComputedRef, DeepReadonly, MaybeRefOrGetter, Raw, Ref } from 'vue';
import { startPromise } from '@shared/utils';
import { logger } from '@/modules/core/common/logging/logging';

const CACHE_EXPIRY = 1000 * 60 * 10;
/** Soft cap: the intended working set. Below it the cache grows without evicting. */
const CACHE_SOFT_SIZE = 500;
/** Hard cap: the resilient ceiling. Only crossing it force-evicts live entries. */
const CACHE_HARD_SIZE = 5000;
const DEBOUNCE_TIME = 800;
/** Minimum gap (ms) between hard-cap warnings so the warning can't itself spam. */
const WARN_THROTTLE = 5000;
/** How long (ms) a failed batch's keys are held back before a retry, to avoid hammering a down backend. */
const FAILURE_BACKOFF = 5000;

interface CacheEntry<T> {
  key: string;
  item: T;
}

/**
 * The persistent storage of an item cache: the resolved values plus the
 * bookkeeping required to decide validity. Decoupled from the cache logic so it
 * can live in an app-lifetime Pinia store and survive composable teardown.
 */
export interface ItemCacheStorage<T> {
  /** Resolved values keyed by identifier. */
  cache: Ref<Record<string, T | null>>;
  /** Per-key expiry timestamps backing the LRU + staleness checks. */
  recent: Map<string, number>;
  /** Identifiers that could not be resolved, with their expiry timestamps. */
  unknown: Map<string, number>;
}

/**
 * Creates a fresh {@link ItemCacheStorage} container.
 *
 * `markRaw` keeps it usable as plain state inside a Pinia store: the `cache` ref
 * and the `Map`s are returned untouched (no reactive proxy that would unwrap the
 * ref or wrap the maps). Reactivity for consumers flows through the `shallowRef`.
 */
export function createItemCacheStorage<T>(): Raw<ItemCacheStorage<T>> {
  // Return the markRaw-branded type so a Pinia store holding this does not
  // deeply unwrap `cache` (Ref) into a plain value — annotating it as the bare
  // ItemCacheStorage<T> would strip the brand and reintroduce the unwrap.
  return markRaw<ItemCacheStorage<T>>({
    cache: shallowRef<Record<string, T | null>>({}),
    recent: new Map<string, number>(),
    unknown: new Map<string, number>(),
  });
}

/**
 * A batch-fetch function that resolves multiple keys at once.
 * Returns a factory that yields {@link CacheEntry} items via an iterator,
 * allowing lazy consumption of potentially large result sets.
 */
type CacheFetch<T> = (keys: string[]) => Promise<() => IterableIterator<CacheEntry<T>>>;

interface CacheOptions<T = unknown> {
  /** Debounce interval (ms) before a queued batch is fetched. @default 800 */
  debounceInMs?: number;
  /** Time-to-live (ms) for cached entries before they become stale. @default 600_000 (10 min) */
  expiry?: number;
  /**
   * Soft cap: the intended working set. The cache grows freely below it; at or
   * above it, an insert first reclaims expired (off-screen) entries. @default 500
   */
  size?: number;
  /**
   * Hard cap: the resilient ceiling. The cache may grow up to here to fit a
   * legitimately large but bounded working set. Only when it is full of *live*
   * entries at this size does an insert force-evict the oldest and emit a
   * throttled warning. Size this from the value's memory weight — light values
   * (numbers, small objects) can be in the thousands, heavy ones (images, long
   * strings) in the hundreds. Clamped up to `size` if set lower. @default 5000
   */
  maxSize?: number;
  /**
   * Identifier used in the hard-cap warning so the offending cache is named in
   * logs (e.g. `'historic-price'`).
   */
  label?: string;
  /**
   * Persistent storage to bind to. When omitted a fresh in-scope storage is
   * created (legacy behaviour). Pass a store-owned {@link ItemCacheStorage} to
   * keep the cache alive across composable teardown.
   */
  storage?: ItemCacheStorage<T>;
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
  /**
   * Synchronously returns the cached value for `key` WITHOUT queueing a fetch.
   * Use this to read a value that some other code is responsible for requesting
   * (e.g. an off-page neighbour) so a read over a large collection can't trigger
   * an unbounded fetch storm.
   */
  peek: (key: string) => T | null;
  /** Clears all cached data, pending state, and unknown entries. */
  reset: () => void;
  /** Forces a re-fetch of the given key regardless of its current cache state. */
  refresh: (key: string) => void;
  /** Removes a key from the cache, the LRU index, the pending set and the unknown map. */
  deleteCacheKey: (key: string) => void;
  /** Removes many keys at once, emitting a single reactive notification. */
  deleteCacheKeys: (keys: string[]) => void;
  /** Queues a key for fetching unless it is already in the unknown map and not yet expired. */
  queueIdentifier: (key: string) => void;
  /** The current number of live entries in the cache (for tests/observability). */
  size: () => number;
}

/**
 * Creates a debounced, reactive item cache backed by a batch-fetch function.
 *
 * Keys requested via {@link ItemCacheReturn.resolve resolve} or
 * {@link ItemCacheReturn.queueIdentifier queueIdentifier} are accumulated into a batch and fetched
 * together after a debounce interval. Unresolvable keys are tracked in an `unknown` map to avoid
 * repeated lookups.
 *
 * ## Resilient capacity
 * The cache grows freely below the soft cap (`size`); above it an insert first reclaims *expired*
 * entries — and since {@link ItemCacheReturn.resolve resolve} refreshes a key's expiry on every read,
 * an entry is "expired" exactly when nothing on screen has read it for `expiry` ms, so the working set
 * tracks what is in use. Only when full of *live* entries at the hard cap (`maxSize`) does it
 * force-evict the oldest and emit a throttled warning — the sign of an unbounded read to fix.
 * Uses `shallowRef` + `triggerRef` so a batch triggers one reactive notification per ref.
 *
 * @param fetch - Batch-fetch function that resolves an array of keys into cache entries.
 * @param options - Optional configuration for debounce timing, expiry, capacity and label.
 */
export function createItemCache<T>(
  fetch: CacheFetch<T>,
  options: CacheOptions<T> = {},
): ItemCacheReturn<T> {
  const {
    debounceInMs = DEBOUNCE_TIME,
    expiry = CACHE_EXPIRY,
    label,
    maxSize = CACHE_HARD_SIZE,
    size: softSize = CACHE_SOFT_SIZE,
    storage,
  } = options;
  // The hard cap can never sit below the soft cap.
  const hardSize = Math.max(softSize, maxSize);
  // Persistent storage is injected so it can outlive this factory instance
  // (e.g. a Pinia store); when absent it falls back to in-scope storage.
  const { cache, recent, unknown } = storage ?? createItemCacheStorage<T>();
  // Transient in-flight state — intentionally factory-local, reset on re-init.
  const pending = shallowRef<Record<string, boolean>>({});
  const batch = new Set<string>();
  let lastWarn = 0;

  /** Removes a key from every store (recent + cache + unknown). Does not notify. */
  const removeEntry = (key: string): void => {
    recent.delete(key);
    delete get(cache)[key];
    if (unknown.has(key))
      unknown.delete(key);
  };

  const warnHardCap = (forced: number): void => {
    const now = Date.now();
    if (now - lastWarn < WARN_THROTTLE)
      return;

    lastWarn = now;
    logger.warn(
      `[item-cache${label ? `:${label}` : ''}] exceeded hard cap of ${hardSize} entries; `
      + `force-evicted ${forced} live entr${forced === 1 ? 'y' : 'ies'}. A consumer is resolving `
      + `more keys than the cap holds (likely an unbounded read) — scope the read to the viewport `
      + `or raise maxSize for this cache.`,
    );
  };

  /**
   * Makes room for one more entry. No-op below the soft cap. At/above it, drops
   * expired entries first (they are the off-screen ones); only if the cache is
   * still full of live entries at the hard cap does it force-evict + warn.
   */
  const evictToFit = (): void => {
    if (recent.size < softSize)
      return;

    const now = Date.now();
    // `recent` is ordered by expiry ascending (every write is delete-then-set
    // with a monotonic `now + expiry`), so the first non-expired entry ends the sweep.
    for (const [key, expiryTs] of recent) {
      if (expiryTs > now)
        break;
      removeEntry(key);
    }

    let forced = 0;
    while (recent.size >= hardSize) {
      const oldest = recent.keys().next().value;
      if (oldest === undefined)
        break;
      removeEntry(oldest);
      forced++;
    }
    if (forced > 0)
      warnHardCap(forced);
  };

  /** Records a key as unresolvable until `expiryTs`, keeping the unknown map bounded. */
  const markUnknown = (key: string, expiryTs: number): void => {
    if (unknown.has(key))
      unknown.delete(key);
    unknown.set(key, expiryTs);

    if (unknown.size <= hardSize)
      return;

    // Bound the negative cache: drop expired first, then oldest, until under cap.
    const now = Date.now();
    for (const [unknownKey, unknownExpiry] of unknown) {
      if (unknownExpiry <= now)
        unknown.delete(unknownKey);
    }
    while (unknown.size > hardSize) {
      const oldest = unknown.keys().next().value;
      if (oldest === undefined)
        break;
      unknown.delete(oldest);
    }
  };

  const deleteCacheKeys = (keys: string[]): void => {
    if (keys.length === 0)
      return;

    const pendingObj = get(pending);
    let pendingChanged = false;
    for (const key of keys) {
      if (pendingObj[key]) {
        delete pendingObj[key];
        pendingChanged = true;
      }
      removeEntry(key);
    }
    if (pendingChanged)
      triggerRef(pending);
    triggerRef(cache);
  };

  const deleteCacheKey = (key: string): void => {
    deleteCacheKeys([key]);
  };

  const setPending = (key: string): void => {
    get(pending)[key] = true;
    triggerRef(pending);

    batch.add(key);
  };

  const put = (key: string, item: T): void => {
    recent.delete(key);
    evictToFit();
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
          markUnknown(key, Date.now() + expiry);
        }
      }
    }
    catch (error) {
      logger.error(error);
      // Transient failure: back the keys off briefly so a down backend is not
      // retried on every debounce tick while the consuming view stays mounted.
      const retryAt = Date.now() + FAILURE_BACKOFF;
      for (const key of keys) markUnknown(key, retryAt);
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

  const peek = (key: string): T | null => get(cache)[key] ?? null;

  const refresh = (key: string): void => {
    // delete-before-set keeps the key at the most-recent end and preserves the
    // expiry-ascending ordering that the eviction sweep relies on.
    recent.delete(key);
    recent.set(key, Date.now() + expiry);
    if (unknown.has(key))
      unknown.delete(key);

    queueIdentifier(key);
  };

  const getIsPending = (identifier: string): boolean => get(pending)[identifier] ?? false;

  const isPending = (
    identifier: MaybeRefOrGetter<string>,
  ): ComputedRef<boolean> => computed<boolean>(() => getIsPending(toValue(identifier)));

  const size = (): number => recent.size;

  const reset = (): void => {
    set(pending, {});
    set(cache, {});
    batch.clear();
    recent.clear();
    unknown.clear();
    lastWarn = 0;
  };

  return {
    cache: readonly(cache),
    deleteCacheKey,
    deleteCacheKeys,
    getIsPending,
    isPending,
    peek,
    queueIdentifier,
    refresh,
    reset,
    resolve,
    size,
    unknown,
  };
}
