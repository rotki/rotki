const CACHE_SIZE = 100;

export const useBlockie = createSharedComposable(() => {
  const cache: Map<string, string> = new Map();

  const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());

  const put = (address: string, image: string) => {
    const cacheSize = Math.max(CACHE_SIZE, 3 * get(itemsPerPage));

    if (cache.size === cacheSize) {
      logger.debug(`Hit cache size of ${cacheSize} going to evict items`);
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
