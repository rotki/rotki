import type { MaybeRef } from '@vueuse/core';

const CACHE_EXPIRY = 1000 * 60 * 10;
const CACHE_SIZE = 500;

export interface CacheEntry<T> {
  key: string;
  item: T;
}

type CacheFetch<T> = (keys: string[]) => Promise<() => IterableIterator<CacheEntry<T>>>;

interface CacheOptions {
  expiry: number;
  size: number;
}

interface UseItemCacheReturn<T> {
  cache: Ref<Record<string, T | null>>;
  unknown: Map<string, number>;
  isPending: (identifier: MaybeRef<string>) => ComputedRef<boolean>;
  retrieve: (key: string) => ComputedRef<T | null>;
  reset: () => void;
  refresh: (key: string) => void;
  deleteCacheKey: (key: string) => void;
  queueIdentifier: (key: string) => void;
}

export function useItemCache<T>(
  fetch: CacheFetch<T>,
  options: CacheOptions = {
    size: CACHE_SIZE,
    expiry: CACHE_EXPIRY,
  },
): UseItemCacheReturn<T> {
  const recent: Map<string, number> = new Map();
  const unknown: Map<string, number> = new Map();
  const cache = ref<Record<string, T | null>>({});
  const pending = ref<Record<string, boolean>>({});
  const batch = ref<string[]>([]);

  const deleteCacheKey = (key: string): void => {
    const copy = { ...get(cache) };
    delete copy[key];
    set(cache, copy);

    if (unknown.has(key))
      unknown.delete(key);
  };

  const updateCacheKey = (key: string, value: T): void => {
    set(cache, { ...get(cache), [key]: value });
  };

  const setPending = (key: string): void => {
    set(pending, { ...get(pending), [key]: true });

    const currentBatch = get(batch);
    if (!currentBatch.includes(key))
      set(batch, [...currentBatch, key]);
  };

  const resetPending = (key: string): void => {
    const copy = { ...get(pending) };
    delete copy[key];
    set(pending, copy);
  };

  const put = (key: string, item: T): void => {
    recent.delete(key);

    if (recent.size === options.size) {
      logger.debug(`Hit cache size of ${options.size} going to evict items`);
      const removeKey = recent.keys().next().value;
      recent.delete(removeKey);
      deleteCacheKey(removeKey);
    }
    recent.set(key, Date.now() + options.expiry);
    updateCacheKey(key, item);
  };

  const fetchBatch = useDebounceFn(() => {
    const currentBatch = get(batch);
    if (currentBatch.length === 0)
      return;

    set(batch, []);
    startPromise(processBatch(currentBatch));
  }, 800);

  async function processBatch(keys: string[]): Promise<void> {
    try {
      const batch = await fetch(keys);
      for (const { item, key } of batch()) {
        if (item) {
          put(key, item);
        }
        else {
          if (import.meta.env.VITE_VERBOSE_CACHE)
            logger.debug(`unknown key: ${key}`);

          recent.delete(key);
          deleteCacheKey(key);

          unknown.set(key, Date.now() + options.expiry);
        }
      }
    }
    catch (error) {
      logger.error(error);
    }
    finally {
      for (const key of keys) resetPending(key);
    }
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

  const retrieve = (key: string): ComputedRef<T | null> => {
    const cached = get(cache)[key];
    const now = Date.now();
    let expired = false;
    if (recent.has(key) && cached) {
      const expiry = recent.get(key);
      recent.delete(key);

      if (expiry && expiry > now) {
        expired = true;
        recent.set(key, now + options.expiry);
      }
    }

    if (!get(pending)[key] && !expired)
      queueIdentifier(key);

    return computed(() => get(cache)[key] ?? null);
  };

  const refresh = (key: string): void => {
    const now = Date.now();
    recent.set(key, now + options.expiry);
    if (unknown.has(key))
      unknown.delete(key);

    queueIdentifier(key);
  };

  const isPending = (
    identifier: MaybeRef<string>,
  ): ComputedRef<boolean> => computed<boolean>(() => get(pending)[get(identifier)] ?? false);

  const reset = (): void => {
    set(pending, {});
    set(cache, {});
    set(batch, []);
    recent.clear();
    unknown.clear();
  };

  return {
    cache,
    unknown,
    isPending,
    retrieve,
    reset,
    refresh,
    deleteCacheKey,
    queueIdentifier,
  };
}
