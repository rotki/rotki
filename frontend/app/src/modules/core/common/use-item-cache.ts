import type { ComputedRef, DeepReadonly, MaybeRefOrGetter, Ref } from 'vue';
import { startPromise } from '@shared/utils';
import { type CacheFetch, createItemCacheStorage, type ItemCacheStorage } from '@/modules/core/common/item-cache-storage';
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

interface CacheOptions<T = unknown> {
  /** Debounce interval in ms before a queued batch is fetched. Defaults to 800. */
  debounceInMs?: number;
  /** Time-to-live in ms before a cached entry goes stale. Defaults to ten minutes. */
  expiry?: number;
  /** Soft cap: below it the cache grows freely, at or above it an insert reclaims expired entries. Defaults to 500. */
  size?: number;
  /**
   * Hard cap: the cache grows to here to fit a large but bounded working set, and only when full of
   * live* entries does an insert force-evict and warn. Size it by value weight, light values in the
   * thousands and heavy ones such as images in the hundreds. Clamped up to `size`. Defaults to 5000.
   */
  maxSize?: number;
  /** Identifier used in the hard-cap warning so the offending cache is named in logs (e.g. `'historic-price'`). */
  label?: string;
  /** Store-owned storage to bind to, to keep the cache alive across composable teardown; omitted = fresh in-scope. */
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
   * Returns the cached value for `key` WITHOUT queueing a fetch — for reading a value some other code
   * is responsible for requesting (e.g. an off-page neighbour), so a wide read can't storm the backend.
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
 * @remarks
 * Keys requested through `resolve`/`queueIdentifier` are batched behind a debounce; misses and
 * failures land in `unknown` so they are not looked up again.
 *
 * Eviction reclaims *expired* entries first, and a read refreshes a key's expiry, so "expired" means
 * nothing on screen has read it for `expiry` ms. Only a cache full of *live* entries at `maxSize`
 * force-evicts the oldest and warns. Each key carries its own version signal, so resolving A never
 * re-runs a computed that reads only B.
 *
 * @param fetch - resolves a whole batch of keys at once; see {@link CacheFetch}
 * @param options - see {@link CacheOptions}
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
  const hardSize = Math.max(softSize, maxSize); // hard cap can never sit below the soft cap
  // Injected storage outlives this factory (e.g. a Pinia store); else in-scope.
  const { cache, recent, unknown } = storage ?? createItemCacheStorage<T>();
  // Fine-grained reactivity: each key gets its own version signal (read subscribes
  // to just its key, write bumps just that key). `values` is the stable record
  // behind `cache` (never reassigned — `reset` clears in place) so reads skip the
  // coarse ref; `cache` is still triggered on structural change for enumeration.
  const values = get(cache);
  const versions = new Map<string, Ref<number>>();
  // Transient in-flight state — intentionally factory-local, reset on re-init.
  const pendingKeys = new Set<string>();
  const batch = new Set<string>();
  let lastWarn = 0;

  /** Subscribes the current reactive effect (if any) to `key`'s changes. */
  const track = (key: string): void => {
    let version = versions.get(key);
    if (!version) {
      version = shallowRef(0);
      versions.set(key, version);
    }
    get(version); // reading the ref registers the dependency
  };

  /** Notifies every effect that read `key` that its value or pending state changed. */
  const bump = (key: string): void => {
    const version = versions.get(key);
    if (version)
      triggerRef(version);
  };

  /** Removes a key from every store (recent + cache + unknown) and notifies its readers. */
  const removeEntry = (key: string): void => {
    recent.delete(key);
    delete values[key];
    if (unknown.has(key))
      unknown.delete(key);
    bump(key);
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

  // Makes room for one more entry: no-op below the soft cap; at/above it drops
  // expired (off-screen) entries first, and only force-evicts + warns when still
  // full of live entries at the hard cap.
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

    for (const key of keys) {
      pendingKeys.delete(key);
      removeEntry(key); // clears value + recent + unknown and bumps the key
    }
    triggerRef(cache);
  };

  const deleteCacheKey = (key: string): void => {
    deleteCacheKeys([key]);
  };

  const setPending = (key: string): void => {
    pendingKeys.add(key);
    bump(key);

    batch.add(key);
  };

  const put = (key: string, item: T): void => {
    recent.delete(key);
    evictToFit();
    recent.set(key, Date.now() + expiry);
    values[key] = item;
    bump(key);
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
          delete values[key];
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
      // Clear pending and notify each key's readers (its resolved state changed).
      for (const key of keys) {
        pendingKeys.delete(key);
        bump(key);
      }
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
    // Non-reactive reads (plain record / Set) so `resolve` only depends via `track`.
    const cached = values[key];
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

    if (!pendingKeys.has(key) && !valid)
      queueIdentifier(key);
  };

  const resolve = (key: string): T | null => {
    ensureQueued(key);
    track(key);
    return values[key] ?? null;
  };

  const peek = (key: string): T | null => {
    track(key);
    return values[key] ?? null;
  };

  const refresh = (key: string): void => {
    // delete-before-set keeps the key at the most-recent end and preserves the
    // expiry-ascending ordering that the eviction sweep relies on.
    recent.delete(key);
    recent.set(key, Date.now() + expiry);
    if (unknown.has(key))
      unknown.delete(key);

    queueIdentifier(key);
  };

  // Tracks `key` so a caller that early-returns on pending before reading the
  // value (e.g. `getHistoricPrice`) still re-runs when pending flips — otherwise
  // it would subscribe to nothing. Outside an effect, `track` is a no-op.
  const getIsPending = (identifier: string): boolean => {
    track(identifier);
    return pendingKeys.has(identifier);
  };

  const isPending = (
    identifier: MaybeRefOrGetter<string>,
  ): ComputedRef<boolean> => computed<boolean>(() => getIsPending(toValue(identifier)));

  const size = (): number => recent.size;

  const reset = (): void => {
    // Clear the record in place so `values` keeps its identity, then wipe the rest.
    for (const key of Object.keys(values)) delete values[key];
    triggerRef(cache);
    pendingKeys.clear();
    batch.clear();
    recent.clear();
    unknown.clear();
    lastWarn = 0;
    for (const version of versions.values()) triggerRef(version); // notify all readers
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
