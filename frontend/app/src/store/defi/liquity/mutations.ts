import {
  LiquityBalances,
  LiquityStaking,
  LiquityStakingEvents,
  TroveEvents
} from '@rotki/common/lib/liquity';
import { MutationTree } from 'vuex';
import { LiquityMutations } from '@/store/defi/liquity/mutation-types';
import { LiquityState } from '@/store/defi/liquity/types';
import { defaultState } from '@/store/defi/state';
import { Writeable } from '@/types';

export const mutations: MutationTree<LiquityState> = {
  [LiquityMutations.SET_BALANCES](
    state: Writeable<LiquityState>,
    balances: LiquityBalances
  ) {
    state.balances = balances;
  },
  [LiquityMutations.SET_EVENTS](
    state: Writeable<LiquityState>,
    events: TroveEvents
  ) {
    state.events = events;
  },
  [LiquityMutations.SET_STAKING](
    state: Writeable<LiquityState>,
    staking: LiquityStaking
  ) {
    state.staking = staking;
  },
  [LiquityMutations.SET_STAKING_EVENTS](
    state: Writeable<LiquityState>,
    events: LiquityStakingEvents
  ) {
    state.stakingEvents = events;
  },
  [LiquityMutations.RESET](state: Writeable<LiquityState>) {
    Object.assign(state, defaultState());
  }
};
