import { MutationTree } from 'vuex';
import { NetValue } from '@/services/types-api';
import { defaultState } from '@/store/statistics/state';
import { StatisticsState } from '@/store/statistics/types';

export const mutations: MutationTree<StatisticsState> = {
  netValue(state: StatisticsState, netValue: NetValue) {
    state.netValue = netValue;
  },
  reset(state: StatisticsState) {
    Object.assign(state, defaultState());
  }
};
