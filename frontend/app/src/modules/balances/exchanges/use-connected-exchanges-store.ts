import type { Exchange } from '@/modules/balances/types/exchanges';
import { set } from '@vueuse/shared';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { ref } from 'vue';

export const useConnectedExchangesStore = defineStore('exchanges', () => {
  const connectedExchanges = ref<Exchange[]>([]);

  const setConnectedExchanges = (exchanges: Exchange[]): void => {
    set(connectedExchanges, exchanges);
  };

  return {
    connectedExchanges,
    setConnectedExchanges,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useConnectedExchangesStore, import.meta.hot));
