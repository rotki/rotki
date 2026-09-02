import type { AddressBookEntry, EthNames } from '@/modules/accounts/address-book/eth-names';
import { createItemCacheStorage } from '@/modules/core/common/item-cache-storage';

/**
 * Holds the display name for every address the app has resolved: ENS names keyed by address, and
 * the richer address-book entries behind them.
 *
 * @remarks
 * State only. `useAddressNameResolution` owns the fetching, batching and eviction, and binds to the
 * {@link ItemCacheStorage} kept here rather than holding one of its own.
 */
export const useAddressNamesStore = defineStore('blockchains/accounts/addresses-names', () => {
  const ensNames = shallowRef<EthNames>({});
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
