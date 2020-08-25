import { GetterTree } from 'vuex';
import { RotkehlchenState } from '@/store/store';
import { TradesState } from './types';

export const getters: GetterTree<TradesState, RotkehlchenState> = {
  showPremium: state => {
    return state.limit > 0 && state.trades.length === state.limit;
  }
};
