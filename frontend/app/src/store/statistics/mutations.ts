import { NetValue } from '@rotki/common/lib/statistics';
import { MutationTree } from 'vuex';
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
