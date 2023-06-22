import { type MaybeRef } from '@vueuse/core';

const CACHE_EXPIRY = 1000 * 60 * 10;
const CACHE_SIZE = 500;

export interface CacheEntry<T> {
  key: string;
  item: T;
}

type CacheFetch<T> = (
  keys: string[]
) => Promise<() => IterableIterator<CacheEntry<T>>>;

interface CacheOptions {
  expiry: number;
  size: number;
}

export const useItemCache = <T>(
  fetch: CacheFetch<T>,
  options: CacheOptions = {
    size: CACHE_SIZE,
    expiry: CACHE_EXPIRY
  }
) => {
  const recent: Map<string, number> = new Map();
  const unknown: Map<string, number> = new Map();
  const cache: Ref<Record<string, T | null>> = ref({});
  const pending: Ref<Record<string, boolean>> = ref({});
  const batch: Ref<string[]> = ref([]);

  const deleteCacheKey = (key: string): void => {
    const copy = { ...get(cache) };
    delete copy[key];
    set(cache, copy);
  };

  const updateCacheKey = (key: string, value: T): void => {
    set(cache, { ...get(cache), [key]: value });
  };

  const setPending = (key: string): void => {
    set(pending, { ...get(pending), [key]: true });

    const currentBatch = get(batch);
    if (!currentBatch.includes(key)) {
      set(batch, [...currentBatch, key]);
    }
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

  const fetchBatch = useDebounceFn(async () => {
    const currentBatch = get(batch);
    if (currentBatch.length === 0) {
      return;
    }
    set(batch, []);
    await processBatch(currentBatch);
  }, 800);

  async function processBatch(keys: string[]): Promise<void> {
    try {
      const batch = await fetch(keys);
      for (const { item, key } of batch()) {
        if (item) {
          put(key, item);
        } else {
          logger.debug(`unknown key: ${key}`);
          unknown.set(key, Date.now() + options.expiry);
        }
      }
    } catch (e) {
      logger.error(e);
    } finally {
      for (const key of keys) {
        resetPending(key);
      }
    }
  }

  const batchPromise = async () => await fetchBatch();

  const queueIdentifier = (key: string): void => {
    const unknownExpiry = unknown.get(key);
    if (unknownExpiry && unknownExpiry >= Date.now()) {
      return;
    }

    if (unknown.has(key)) {
      unknown.delete(key);
    }
    setPending(key);
    startPromise(batchPromise());
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

    if (!get(pending)[key] && !expired) {
      queueIdentifier(key);
    }

    return computed(() => get(cache)[key] ?? null);
  };

  const isPending = (identifier: MaybeRef<string>): ComputedRef<boolean> =>
    computed(() => get(pending)[get(identifier)] ?? false);

  const reset = (): void => {
    set(pending, {});
    set(cache, {});
    set(batch, []);
    recent.clear();
    unknown.clear();
  };

  return {
    cache,
    isPending,
    retrieve,
    reset,
    deleteCacheKey
  };
};
