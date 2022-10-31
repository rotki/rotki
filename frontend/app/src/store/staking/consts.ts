import i18n from '@/i18n';
import { ActionDataEntry } from '@/store/types';
import { KrakenStakingEventType } from '@/types/staking';

export const krakenStakingEventTypeData = computed<ActionDataEntry[]>(() => [
  {
    identifier: KrakenStakingEventType.REWARD,
    label: i18n.t('kraken_staking_events.types.staking_reward').toString()
  },
  {
    identifier: KrakenStakingEventType.RECEIVE_WRAPPED,
    label: i18n.t('kraken_staking_events.types.receive_staked_asset').toString()
  },
  {
    identifier: KrakenStakingEventType.DEPOSIT_ASSET,
    label: i18n.t('kraken_staking_events.types.stake_asset').toString()
  },
  {
    identifier: KrakenStakingEventType.REMOVE_ASSET,
    label: i18n.t('kraken_staking_events.types.unstake_asset').toString()
  }
]);
