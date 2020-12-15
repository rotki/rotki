import {
  ADEX_BALANCES,
  ADEX_HISTORY,
  ETH2_DEPOSITS,
  ETH2_DETAILS,
  RESET
} from '@/store/staking/consts';
import {
  AdexBalances,
  AdexHistory,
  Eth2Deposit,
  Eth2Detail,
  StakingState
} from '@/store/staking/types';
import { defaultState } from '@/store/statistics/state';
import { Writeable } from '@/types';

type Mutations<S = StakingState> = {
  [ETH2_DETAILS](state: S, details: Eth2Detail[]): void;
  [ETH2_DEPOSITS](state: S, deposits: Eth2Deposit[]): void;
  [ADEX_BALANCES](state: S, balances: AdexBalances): void;
  [ADEX_HISTORY](state: S, events: AdexHistory): void;
  [RESET](state: S): void;
};

export const mutations: Mutations = {
  [ETH2_DETAILS](state: Writeable<StakingState>, details: Eth2Detail[]) {
    state.eth2Details = details;
  },
  [ETH2_DEPOSITS](state: Writeable<StakingState>, details: Eth2Deposit[]) {
    state.eth2Deposits = details;
  },
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
