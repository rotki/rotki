import { Module } from '@/types/modules';

export const useStakingStore = defineStore('staking', () => {
  const { reset: resetEth2 } = useEth2StakingStore();

  const reset = (module?: Module): void => {
    if (!module || module === Module.ETH2) {
      resetEth2();
    }
  };

  return {
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useStakingStore, import.meta.hot));
}
