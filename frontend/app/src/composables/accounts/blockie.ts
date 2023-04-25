import { useItemCache } from '@/composables/item-cache';
import { createBlockie } from '@/utils/blockie';

const CACHE_SIZE = 200;

export const useBlockie = createSharedComposable(() => {
  const getBlockies = async (addresses: string[]) =>
    function* () {
      for (const address of addresses) {
        const formatted = address.toLowerCase();
        const blockie = createBlockie({
          seed: formatted
        });

        yield { key: address, item: blockie };
      }
    };
  const { cache, retrieve, isPending } = useItemCache<string>(
    keys => getBlockies(keys),
    {
      size: CACHE_SIZE,
      expiry: -1
    }
  );

  const getBlockie = (address: string | null = '') => {
    if (!address) {
      return '';
    }

    const formatted = address.toLowerCase();
    return get(retrieve(formatted)) || '';
  };

  return {
    cache,
    isPending,
    getBlockie
  };
});
