import { assert } from '@rotki/common';
import { createBlockie } from '@rotki/ui-library';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { logger } from '@/utils/logging';

const CACHE_SIZE = 100;

interface UseBlockieReturn {
  cache: Map<string, string>;
  getBlockie: (address?: string | null) => string;
}

export const useBlockie = createSharedComposable((): UseBlockieReturn => {
  const cache: Map<string, string> = new Map();

  const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());

  const put = (address: string, image: string): void => {
    const cacheSize = Math.max(CACHE_SIZE, 3 * get(itemsPerPage));

    if (cache.size === cacheSize) {
      logger.debug(`Hit cache size of ${cacheSize} going to evict items`);
      const removeKey = cache.keys().next().value;
      assert(removeKey, 'removeKey is null');
      cache.delete(removeKey);
    }
    cache.set(address, image);
  };

  const getBlockie = (address: string | null = ''): string => {
    if (!address)
      return '';

    const formatted = address.toLowerCase();

    if (!cache.has(formatted)) {
      const blockie = createBlockie({
        seed: formatted,
      });

      put(formatted, blockie);
    }

    return cache.get(formatted) || '';
  };

  return {
    cache,
    getBlockie,
  };
});
