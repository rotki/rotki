import type { EthNames } from '@/modules/accounts/address-book/eth-names';

export const useAddressNamesStore = defineStore('blockchains/accounts/addresses-names', () => {
  const ensNames = shallowRef<EthNames>({});

  function setEnsNames(newResult: Record<string, string | null>): void {
    set(ensNames, {
      ...get(ensNames),
      ...newResult,
    });
  }

  return {
    ensNames,
    setEnsNames,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAddressNamesStore, import.meta.hot));
