import { LiquityBalances, LiquityEvents } from '@rotki/common/lib/liquity';
import { MutationTree } from 'vuex';
import { LiquityMutations } from '@/store/defi/liquity/mutation-types';
import { LiquitityState } from '@/store/defi/liquity/types';
import { defaultState } from '@/store/defi/state';
import { Writeable } from '@/types';

export const mutations: MutationTree<LiquitityState> = {
  [LiquityMutations.SET_BALANCES](
    state: Writeable<LiquitityState>,
    balances: LiquityBalances
  ) {
    state.balances = balances;
  },
  [LiquityMutations.SET_EVENTS](
    state: Writeable<LiquitityState>,
    events: LiquityEvents
  ) {
    state.events = events;
  },
  [LiquityMutations.RESET](state: Writeable<LiquitityState>) {
    Object.assign(state, defaultState());
  }
};
