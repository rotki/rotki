import { AdexBalances, AdexHistory } from '@rotki/common/lib/staking/adex';
import { ADEX_BALANCES, ADEX_HISTORY, RESET } from '@/store/staking/consts';
import { StakingState } from '@/store/staking/types';
import { defaultState } from '@/store/statistics/state';
import { Writeable } from '@/types';

type Mutations<S = StakingState> = {
  [ADEX_BALANCES](state: S, balances: AdexBalances): void;
  [ADEX_HISTORY](state: S, events: AdexHistory): void;
  [RESET](state: S): void;
};

export const mutations: Mutations = {
  [ADEX_BALANCES](state: Writeable<StakingState>, balances: AdexBalances) {
    state.adexBalances = balances;
  },
  [ADEX_HISTORY](state: Writeable<StakingState>, history: AdexHistory) {
    state.adexHistory = history;
  },
  [RESET](state: StakingState) {
    Object.assign(state, defaultState());
  }
};
