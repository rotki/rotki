import { Eth2Deposit, Eth2Detail, StakingState } from '@/store/staking/types';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';

interface StakingGetters {
  deposits: Eth2Deposit[];
  details: Eth2Detail[];
}

export const getters: Getters<
  StakingState,
  StakingGetters,
  RotkehlchenState,
  any
> = {
  deposits: state => state.eth2Deposits,
  details: state => state.eth2Details
};
