import {
  Eth2DailyStats,
  Eth2Deposits,
  Eth2Details
} from '@rotki/common/lib/staking/eth2';
import { StakingState } from '@/store/staking/types';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';

interface StakingGetters {
  deposits: Eth2Deposits;
  details: Eth2Details;
  stats: Eth2DailyStats;
}

export const getters: Getters<
  StakingState,
  StakingGetters,
  RotkehlchenState,
  any
> = {
  deposits: state => state.eth2Deposits,
  details: state => state.eth2Details,
  stats: state => state.eth2DailyStats
};
