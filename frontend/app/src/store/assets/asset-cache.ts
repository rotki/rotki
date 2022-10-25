import { AssetInfo } from '@rotki/common/lib/data';
import { ComputedRef, Ref } from 'vue';
import { useAssetInfoApi } from '@/services/assets/info';
import { startPromise } from '@/utils';
import { logger } from '@/utils/logging';

const CACHE_EXPIRY = 1000 * 60 * 10;
const CACHE_SIZE = 500;

export const useAssetCacheStore = defineStore('assets/cache', () => {
  const recent: Map<string, number> = new Map();
  const unknown: Map<string, number> = new Map();
  const cache: Ref<Record<string, AssetInfo | null>> = ref({});
  const pending: Ref<Record<string, boolean>> = ref({});
  const batch: Ref<string[]> = ref([]);

  const { assetMapping } = useAssetInfoApi();

  const deleteCacheKey = (key: string): void => {
    const copy = { ...get(cache) };
    delete copy[key];
    set(cache, copy);
  };

  const updateCacheKey = (key: string, value: AssetInfo): void => {
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

  const put = (key: string, asset: AssetInfo): void => {
    recent.delete(key);

    if (recent.size === CACHE_SIZE) {
      logger.debug(`Hit cache size of ${CACHE_SIZE} going to evict items`);
      const removeKey = recent.keys().next().value;
      recent.delete(removeKey);
      deleteCacheKey(removeKey);
    }
    recent.set(key, Date.now() + CACHE_EXPIRY);
    updateCacheKey(key, asset);
  };

  const fetchBatch = useDebounceFn(async () => {
    const currentBatch = get(batch);
    set(batch, []);
    await fetchAssets(currentBatch);
  }, 800);

  async function fetchAssets(keys: string[]): Promise<void> {
    try {
      const response = await assetMapping(keys);
      for (const key of keys) {
        if (response[key]) {
          put(key, response[key]);
        } else {
          logger.debug(`unknown key: ${key}`);
          unknown.set(key, Date.now() + CACHE_EXPIRY);
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

  const retrieve = (key: string): ComputedRef<AssetInfo | null> => {
    const cached = get(cache)[key];
    const now = Date.now();
    let expired = false;
    if (recent.has(key) && cached) {
      const expiry = recent.get(key);
      recent.delete(key);

      if (expiry && expiry > now) {
        expired = true;
        recent.set(key, now + CACHE_EXPIRY);
      }
    }

    if (!get(pending)[key] && !expired) {
      queueIdentifier(key);
    }

    return computed(() => get(cache)[key] ?? null);
  };

  const isPending = (identifier: string): ComputedRef<boolean> => {
    return computed(() => get(pending)[identifier] ?? false);
  };

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
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useAssetCacheStore, import.meta.hot));
}
