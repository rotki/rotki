import type {
  LiquityBalancesWithCollateralInfo,
  LiquityPoolDetails,
  LiquityStakingDetails,
  LiquityStatistics,
} from '@rotki/common';

const defaultBalances = (): LiquityBalancesWithCollateralInfo => ({ balances: {}, totalCollateralRatio: null });

export const useLiquityStore = defineStore('defi/liquity', () => {
  const balances = ref<LiquityBalancesWithCollateralInfo>(defaultBalances());
  const staking = ref<LiquityStakingDetails>({});
  const stakingPools = ref<LiquityPoolDetails>({});
  const statistics = ref<LiquityStatistics | null>(null);

  return {
    balances,
    staking,
    stakingPools,
    statistics,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useLiquityStore, import.meta.hot));
