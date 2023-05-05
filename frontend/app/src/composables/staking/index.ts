import { Module } from '@/types/modules';

export const useStaking = () => {
  const { $reset } = useEth2StakingStore();

  const reset = (module?: Module): void => {
    if (!module || module === Module.ETH2) {
      $reset();
    }
  };

  return {
    reset
  };
};
