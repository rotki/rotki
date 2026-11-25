import type { PremiumCapabilities } from '@/modules/session/types';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { ref } from 'vue';

export const usePremiumStore = defineStore('session/premium', () => {
  const premium = ref<boolean>(false);
  const premiumSync = ref<boolean>(false);
  const capabilities = ref<PremiumCapabilities>();

  return {
    capabilities,
    premium,
    premiumSync,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(usePremiumStore, import.meta.hot));
