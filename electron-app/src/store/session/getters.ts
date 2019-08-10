import { GetterTree } from 'vuex';
import { BalanceState } from '@/store/balances/state';
import { RotkehlchenState } from '@/store';
import { SessionState } from '@/store/session/state';

export const getters: GetterTree<SessionState, RotkehlchenState> = {
  floatingPrecision: (state: SessionState) => {
    return state.settings.floatingPrecision;
  },
  dateDisplayFormat: (state: SessionState) => {
    return state.settings.dateDisplayFormat;
  }
};
