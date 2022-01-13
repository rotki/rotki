import { StakingState } from '@/store/staking/types';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';

interface StakingGetters {}

export const getters: Getters<
  StakingState,
  StakingGetters,
  RotkehlchenState,
  any
> = {};
