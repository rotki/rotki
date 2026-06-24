import type { AddressBookEntry, EthNames } from '@/modules/accounts/address-book/eth-names';
import { createItemCacheStorage } from '@/modules/core/common/use-item-cache';

export const useAddressNamesStore = defineStore('blockchains/accounts/addresses-names', () => {
  const ensNames = shallowRef<EthNames>({});
  // App-lifetime cache storage for resolved address names; the fetch/debounce/LRU
  // logic lives in useAddressNameResolution, which binds to this so the cache
  // survives composable teardown instead of being wiped at zero subscribers.
  const addressNameStorage = createItemCacheStorage<AddressBookEntry | undefined>();

  function setEnsNames(newResult: Record<string, string | null>): void {
    set(ensNames, {
      ...get(ensNames),
      ...newResult,
    });
  }

  return {
    addressNameStorage,
    ensNames,
    setEnsNames,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAddressNamesStore, import.meta.hot));
