import {
  AdexBalances,
  AdexEvents,
  Eth2Deposit,
  Eth2Detail,
  StakingState
} from '@/store/staking/types';
import { defaultState } from '@/store/statistics/state';
import { Writeable } from '@/types';

type Mutations<S = StakingState> = {
  eth2Details(state: S, details: Eth2Detail[]): void;
  eth2Deposits(state: S, deposits: Eth2Deposit[]): void;
  adexBalances(state: S, balances: AdexBalances): void;
  adexEvents(state: S, events: AdexEvents): void;
  reset(state: S): void;
};

export const mutations: Mutations = {
  eth2Details(state: Writeable<StakingState>, details: Eth2Detail[]) {
    state.eth2Details = details;
  },
  eth2Deposits(state: Writeable<StakingState>, details: Eth2Deposit[]) {
    state.eth2Deposits = details;
  },
  adexBalances(state: Writeable<StakingState>, balances: AdexBalances) {
    state.adexBalances = balances;
  },
  adexEvents(state: Writeable<StakingState>, events: AdexEvents) {
    state.adexEvents = events;
  },
  reset(state: StakingState) {
    Object.assign(state, defaultState());
  }
};
