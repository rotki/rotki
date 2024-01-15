import type {
  Eth2StakingRewards,
  EthStakingPayload,
} from '@rotki/common/lib/staking/eth2';
import type { MaybeRef } from '@vueuse/core';

export function useEth2Rewards() {
  const { fetchStakingRewards } = useEth2StakingStore();

  const {
    state: rewards,
    execute,
    isLoading: loading,
  } = useAsyncState<Eth2StakingRewards, MaybeRef<EthStakingPayload>[]>(
    fetchStakingRewards,
    {
      executionLayerRewards: Zero,
      withdrawnConsensusLayerRewards: Zero,
    },
    {
      immediate: false,
      resetOnExecute: false,
      delay: 0,
    },
  );

  const fetchRewards = async (
    payload: MaybeRef<EthStakingPayload>,
  ): Promise<void> => {
    await execute(0, payload);
  };

  return {
    loading,
    rewards,
    fetchRewards,
  };
}
