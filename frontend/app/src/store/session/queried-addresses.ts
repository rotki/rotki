import type { QueriedAddresses } from '@/types/session';

export const useQueriedAddressesStore = defineStore('session/queried-addresses', () => {
  const queriedAddresses = ref<QueriedAddresses>({});

  return {
    queriedAddresses,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useQueriedAddressesStore, import.meta.hot));
