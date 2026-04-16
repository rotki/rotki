import type {
  CommonQueryStatusData,
  LiquityBalancesWithCollateralInfo,
  LiquityPoolDetails,
  LiquityStakingDetails,
  LiquityStatistics,
} from '@rotki/common';
import { Section } from '@/modules/core/common/status';
import { useStatusUpdater } from '@/modules/shell/sync-progress/use-status-updater';

const defaultBalances = (): LiquityBalancesWithCollateralInfo => ({ balances: {}, totalCollateralRatio: null });

export const useLiquityStore = defineStore('defi/liquity', () => {
  const balances = ref<LiquityBalancesWithCollateralInfo>(defaultBalances());
  const staking = ref<LiquityStakingDetails>({});
  const stakingPools = ref<LiquityPoolDetails>({});
  const statistics = ref<LiquityStatistics | null>(null);

  const stakingQueryStatus = ref<CommonQueryStatusData>();

  const reset = (): void => {
    const { resetStatus } = useStatusUpdater(Section.DEFI_LIQUITY_BALANCES);

    set(balances, defaultBalances());
    set(staking, {});
    set(statistics, null);

    resetStatus({ section: Section.DEFI_LIQUITY_BALANCES });
    resetStatus({ section: Section.DEFI_LIQUITY_STAKING });
    resetStatus({ section: Section.DEFI_LIQUITY_STATISTICS });
  };

  const setStakingQueryStatus = (data: CommonQueryStatusData | null): void => {
    set(stakingQueryStatus, data);
  };

  return {
    balances,
    reset,
    setStakingQueryStatus,
    staking,
    stakingPools,
    stakingQueryStatus,
    statistics,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useLiquityStore, import.meta.hot));
