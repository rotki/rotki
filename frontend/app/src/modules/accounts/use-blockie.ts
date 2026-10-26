import { assert } from '@rotki/common';
import { createBlockie } from '@rotki/ui-library';

/**
 * Blockies kept at once.
 *
 * @remarks
 * Every unknown token gets a blockie drawn on a canvas, so an address holding a few hundred spam
 * tokens needs that many in one list. A cache smaller than the list redraws them each time the list
 * renders again. An entry is a small data URL, so a thousand of them stay well under a few MB.
 */
const CACHE_SIZE = 1000;

interface UseBlockieReturn {
  cache: Map<string, string>;
  getBlockie: (address?: string | null) => string;
}

export const useBlockie = createSharedComposable((): UseBlockieReturn => {
  const cache: Map<string, string> = new Map();

  /** Stores a blockie, dropping the least recently used one once the cache is full. */
  const put = (address: string, image: string): void => {
    if (cache.size >= CACHE_SIZE) {
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
    const cached = cache.get(formatted);
    if (cached !== undefined) {
      cache.delete(formatted);
      cache.set(formatted, cached);
      return cached;
    }

    const blockie = createBlockie({ seed: formatted });
    put(formatted, blockie);
    return blockie;
  };

  return {
    cache,
    getBlockie,
  };
});
