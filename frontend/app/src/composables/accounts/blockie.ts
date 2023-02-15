import { logger } from '@/utils/logging';
import { createBlockie } from '@/utils/blockie';

const CACHE_SIZE = 100;

export const useBlockie = createSharedComposable(() => {
  const cache: Map<string, string> = new Map();

  const put = (address: string, image: string) => {
    if (cache.size === CACHE_SIZE) {
      logger.debug(`Hit cache size of ${CACHE_SIZE} going to evict items`);
      const removeKey = cache.keys().next().value;
      cache.delete(removeKey);
    }
    cache.set(address, image);
  };

  const getBlockie = (address: string | null = '') => {
    if (!address) {
      return '';
    }

    const formatted = address.toLowerCase();

    if (!cache.has(formatted)) {
      const blockie = createBlockie({
        seed: formatted
      });

      put(formatted, blockie);
    }

    return cache.get(formatted) || '';
  };

  return {
    cache,
    getBlockie
  };
});
