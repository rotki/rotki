import { type ComputedRef } from 'vue';
import { KrakenStakingEventType } from '@/types/staking';
import { type ActionDataEntry } from '@/types/action';

export const useKrakenStakingEventTypes = (): {
  krakenStakingEventTypeData: ComputedRef<ActionDataEntry[]>;
} => {
  const { tc } = useI18n();
  const krakenStakingEventTypeData: ComputedRef<ActionDataEntry[]> = computed(
    () => [
      {
        identifier: KrakenStakingEventType.REWARD,
        label: tc('kraken_staking_events.types.staking_reward')
      },
      {
        identifier: KrakenStakingEventType.RECEIVE_WRAPPED,
        label: tc('kraken_staking_events.types.receive_staked_asset')
      },
      {
        identifier: KrakenStakingEventType.DEPOSIT_ASSET,
        label: tc('kraken_staking_events.types.stake_asset')
      },
      {
        identifier: KrakenStakingEventType.REMOVE_ASSET,
        label: tc('kraken_staking_events.types.unstake_asset')
      }
    ]
  );

  return {
    krakenStakingEventTypeData
  };
};
