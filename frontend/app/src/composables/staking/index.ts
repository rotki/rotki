import { Module } from '@/types/modules';

export const useStaking = () => {
  const { reset: resetEth2 } = useEth2StakingStore();

  const reset = (module?: Module): void => {
    if (!module || module === Module.ETH2) {
      resetEth2();
    }
  };

  return {
    reset
  };
};
