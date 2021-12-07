import { useStore } from '@/store/utils';

export const setupStaking = () => {
  const store = useStore();
  const fetchEth2StakingDetails = async (refresh: boolean = false) => {
    await store.dispatch('staking/fetchStakingDetails', refresh);
  };
  return {
    fetchEth2StakingDetails
  };
};
