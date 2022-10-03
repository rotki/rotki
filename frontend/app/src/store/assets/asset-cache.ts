import { AssetInfo } from '@rotki/common/lib/data';
import { ComputedRef, Ref } from 'vue';
import { useAssetInfoApi } from '@/services/assets/info';
import { startPromise } from '@/utils';
import { logger } from '@/utils/logging';

const CACHE_EXPIRY = 1000 * 60 * 10;
const CACHE_SIZE = 200;

export const useAssetCacheStore = defineStore('assets/cache', () => {
  const recent: Map<string, number> = new Map();
  const unknown: Map<string, number> = new Map();
  const cache: Ref<Record<string, AssetInfo | null>> = ref({});
  const pending: Ref<Record<string, boolean>> = ref({});

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
  };

  const resetPending = (key: string): void => {
    const copy = { ...get(pending) };
    delete copy[key];
    set(pending, copy);
  };

  const put = (key: string, asset: AssetInfo): void => {
    recent.delete(key);

    if (recent.size === CACHE_SIZE) {
      const removeKey = recent.keys().next().value;
      recent.delete(removeKey);
      deleteCacheKey(removeKey);
    }
    recent.set(key, Date.now() + CACHE_EXPIRY);
    updateCacheKey(key, asset);
  };

  const queueFetch = async (key: string): Promise<void> => {
    setPending(key);
    const unknownExpiry = unknown.get(key);
    if (unknownExpiry && unknownExpiry >= Date.now()) {
      return;
    }

    if (unknown.has(key)) {
      unknown.delete(key);
    }

    try {
      const response = await assetMapping([key]);
      if (response[key]) {
        put(key, response[key]);
      } else {
        logger.debug(`unknown key: ${key}`);
        unknown.set(key, Date.now() + CACHE_EXPIRY);
      }
    } finally {
      resetPending(key);
    }
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
      startPromise(queueFetch(key));
    }

    return computed(() => get(cache)[key] ?? null);
  };

  const reset = (): void => {
    set(pending, {});
    set(cache, {});
    recent.clear();
    unknown.clear();
  };

  return {
    cache,
    retrieve,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useAssetCacheStore, import.meta.hot));
}
