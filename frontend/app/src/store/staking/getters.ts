import { Eth2Deposit, Eth2Total, StakingState } from '@/store/staking/types';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';

interface StakingGetters {
  deposits: Eth2Deposit[];
  total: Eth2Total;
}

export const getters: Getters<
  StakingState,
  StakingGetters,
  RotkehlchenState,
  any
> = {
  deposits: state => state.eth2.deposits,
  total: state => state.eth2.totals
};
